"""CSV runner. Defaults to preview; credentials are read only from the environment."""

import argparse
import csv
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


FIELDS = ["box_name", "rack_slot_id", "layout", "parent_path", "position_count", "box_id", "status", "error"]
ENDPOINT = "/plugin/inventree-bulk-plugin/bulkcreate"


class BatchError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BatchError("Unexpected redirect; check INVENTREE_URL.")


class Client:
    def __init__(self, url, token):
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise BatchError("INVENTREE_URL must be a server URL without credentials, query, or fragment.")
        if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise BatchError("Use HTTPS, or an HTTP localhost SSH tunnel.")
        self.url, self.token = url.rstrip("/"), token
        self.opener = build_opener(NoRedirect())

    def request(self, path, data=None):
        req = Request(self.url + path, data=json.dumps(data).encode() if data is not None else None,
                      headers={"Authorization": "Token " + self.token, "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=120) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.load(exc)
                message = str(detail.get("detail", detail.get("error", detail)))
            except (ValueError, AttributeError):
                message = "Server rejected the request."
            raise BatchError(f"HTTP {exc.code}: {message}".replace(self.token, "[redacted]")) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise BatchError("Connection or response failure; rerun preflight to reconcile server state.") from None

    def preview(self, row):
        location = self.request(f"/api/stock/location/{row['rack_slot_id']}/")
        row["parent_path"] = location["pathstring"]
        return self.request(ENDPOINT, payload(row))

    def create(self, row):
        return self.request(ENDPOINT + "?create=true", payload(row))


def payload(row):
    return {"mode": "freezer_box", "parent_id": int(row["rack_slot_id"]),
            "box_name": row["box_name"], "layout": row["layout"]}


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["box_name", "rack_slot_id", "layout"]:
            raise BatchError("CSV header must be box_name,rack_slot_id,layout")
        rows = []
        for number, source in enumerate(reader, 2):
            if None in source or any(value is None for value in source.values()):
                raise BatchError(f"CSV row {number} has the wrong number of fields.")
            row = {key: value.strip() for key, value in source.items()}
            row.update(status="pending", error="")
            if not row["box_name"] or not row["rack_slot_id"].isascii() or not row["rack_slot_id"].isdigit() or int(row["rack_slot_id"]) < 1 or row["layout"] not in ("9x9", "10x10"):
                row.update(status="failed", error=f"Invalid name, slot ID, or layout on row {number}.")
            else:
                row["rack_slot_id"] = str(int(row["rack_slot_id"]))
            rows.append(row)
    if not rows:
        raise BatchError("CSV contains no boxes.")
    seen = {}
    for row in rows:
        key = row["rack_slot_id"]
        if key in seen:
            for duplicate in (seen[key], row):
                duplicate.update(status="failed", error="Duplicate rack-slot assignment in CSV.")
        seen[key] = row
    return rows


def write_report(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            # Prevent spreadsheet software from evaluating user-supplied formula text.
            writer.writerow({k: ("'" + str(v) if str(v).startswith(("=", "+", "-", "@", "\t", "\r")) else v) for k, v in row.items()})
        temporary = handle.name
    os.replace(temporary, path)


def run_batch(rows, client, report, *, apply=False):
    for row in rows:
        if row["status"] == "failed":
            continue
        try:
            result = client.preview(row)
            row.update({key: result.get(key, "") for key in ("parent_path", "position_count", "box_id")})
            row["status"] = "skipped" if result["status"] == "already_exists" else "ready"
        except BatchError as exc:
            row.update(status="failed", error=str(exc))
        write_report(report, rows)
    write_report(report, rows)
    if any(row["status"] == "failed" for row in rows):
        return 1
    if apply:
        for row in rows:
            if row["status"] == "skipped":
                continue
            try:
                result = client.create(row)
                row.update(box_id=result["box_id"], status="created" if result["status"] == "created" else "skipped")
            except BatchError as exc:
                row.update(status="failed", error=str(exc))
                for remaining in rows:
                    if remaining["status"] == "ready":
                        remaining["status"] = "not_attempted"
                write_report(report, rows)
                return 1
            write_report(report, rows)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--apply", action="store_true", help="Create after every row passes preflight")
    parser.add_argument("--report", type=Path, default=Path("freezer-box-results.csv"))
    args = parser.parse_args(argv)
    try:
        if args.csv_file.resolve() == args.report.resolve():
            raise BatchError("Report must not overwrite the input CSV.")
        url, token = os.environ.get("INVENTREE_URL"), os.environ.get("INVENTREE_TOKEN")
        if not url or not token:
            raise BatchError("Set INVENTREE_URL and INVENTREE_TOKEN in the environment.")
        rows = read_csv(args.csv_file)
        code = run_batch(rows, Client(url, token), args.report, apply=args.apply)
        for row in rows:
            print(f"{row['status']}: {row['box_name']} → {row.get('parent_path', row['rack_slot_id'])} ({row.get('position_count', '?')} positions)")
        print(f"Report: {args.report}")
        return code
    except (BatchError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
