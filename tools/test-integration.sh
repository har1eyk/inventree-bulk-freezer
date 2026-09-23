#!/bin/sh
# Run inside tools/test-compose.yml's disposable app container.
set -eu
python -m pip install /release/dist/*.whl django-test-migrations django-slowtests
python src/backend/InvenTree/manage.py migrate --noinput
python src/backend/InvenTree/manage.py shell < /release/tools/prepare_test_instance.py
python src/backend/InvenTree/manage.py migrate --noinput
# Require the plugin migration explicitly after fresh registry discovery.
python src/backend/InvenTree/manage.py migrate inventree_bulk_plugin --noinput
python src/backend/InvenTree/manage.py collectstatic --noinput
python -m unittest discover -s /release/inventree_bulk_plugin/tests/unit -t /release
python src/backend/InvenTree/manage.py test inventree_bulk_plugin.tests.integration.test_freezer --noinput
