# Development

```sh
cd inventree_bulk_plugin/frontend
npm ci
npm run build
cd ../..
python -m build
python -m unittest inventree_bulk_plugin.tests.unit.test_batch
```

In an isolated InvenTree 1.3.2 container with PostgreSQL, install the fork and set
`INVENTREE_PLUGINS_ENABLED=True`, `INVENTREE_PLUGINS_MANDATORY=inventree-bulk-plugin`,
`INVENTREE_PLUGIN_TESTING=True`, and `INVENTREE_PLUGIN_TESTING_SETUP=True`. After migrations:

```sh
python src/backend/InvenTree/manage.py test inventree_bulk_plugin.tests.integration.test_freezer --noinput
```

See [VALIDATION.md](../VALIDATION.md) for performed checks. Do not point test commands
at a production database. Frontend assets are bundled in the wheel; no CDN is used.

## Reproduce the release checks with Docker

Build the frontend and distributions first, then run:

```sh
docker compose -p freezer-test -f tools/test-compose.yml up -d
docker compose -p freezer-test -f tools/test-compose.yml exec -T app sh /release/tools/test-integration.sh
docker compose -p freezer-test -f tools/test-compose.yml down -v
```

This creates a disposable PostgreSQL database and an InvenTree 1.3.2 instance.
It does not mount any production data. The loopback-only port 18437 is reserved
for optional manual browser checks. The password in the compose file is only
for the disposable test database; never reuse this configuration for production.
Keep only the wheel being tested in `dist/` before running the script.

## Publishing

Update the version and changelog, run the checks, and create a matching Git tag
(e.g. `v1.5.2.post2`). Publishing a GitHub release triggers `publish.yml`, which
runs the checks again, attaches the validated wheel/source archive/checksums, and
publishes the packages to PyPI using Trusted Publishing. Configure the PyPI
publisher for repository `har1eyk/inventree-bulk-freezer`, workflow `publish.yml`,
and environment `pypi`. Pull requests and ordinary pushes cannot publish.

The README uses versioned absolute screenshot URLs so images also render on PyPI.
Update these links when preparing a release with new screenshots. Use only
fictional inventory in screenshots; do not capture production data.
