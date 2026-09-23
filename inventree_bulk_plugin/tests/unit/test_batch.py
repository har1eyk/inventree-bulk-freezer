import csv
from pathlib import Path
import tempfile
import unittest

from inventree_bulk_plugin.batch import BatchError, read_csv, run_batch


class FakeClient:
    def __init__(self):
        self.boxes = {}
        self.calls = []
        self.fail = None

    def preview(self, row):
        return {"status": "already_exists" if row["rack_slot_id"] in self.boxes else "ready", "parent_path": "Freezer/Slot " + row["rack_slot_id"], "position_count": 81, "box_id": self.boxes.get(row["rack_slot_id"])}

    def create(self, row):
        self.calls.append(row["rack_slot_id"])
        if row["rack_slot_id"] == self.fail:
            raise BatchError("Injected network failure")
        self.boxes[row["rack_slot_id"]] = 100 + int(row["rack_slot_id"])
        return {"status": "created", "box_id": self.boxes[row["rack_slot_id"]]}


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "boxes.csv"
        self.report = Path(self.directory.name) / "results.csv"
        self.source.write_text("box_name,rack_slot_id,layout\nBox 1,1,9x9\nBox 2,2,9x9\nBox 3,3,10x10\n")

    def test_preview_never_creates(self):
        client = FakeClient()
        self.assertEqual(run_batch(read_csv(self.source), client, self.report), 0)
        self.assertEqual(client.calls, [])
        self.assertIn("Freezer/Slot 1", self.report.read_text())

    def test_stop_and_resume(self):
        client = FakeClient()
        client.fail = "2"
        self.assertEqual(run_batch(read_csv(self.source), client, self.report, apply=True), 1)
        self.assertEqual(client.calls, ["1", "2"])
        self.assertIn("not_attempted", self.report.read_text())
        client.fail = None
        self.assertEqual(run_batch(read_csv(self.source), client, self.report, apply=True), 0)
        self.assertEqual(client.calls, ["1", "2", "2", "3"])
        with self.report.open() as handle:
            self.assertEqual(next(csv.DictReader(handle))["status"], "skipped")

    def test_duplicate_slots_and_invalid_layout_block_entire_batch(self):
        self.source.write_text("box_name,rack_slot_id,layout\nOne,1,9x9\nTwo,01,9x9\nThree,3,8x8\n")
        client = FakeClient()
        self.assertEqual(run_batch(read_csv(self.source), client, self.report, apply=True), 1)
        self.assertEqual(client.calls, [])
