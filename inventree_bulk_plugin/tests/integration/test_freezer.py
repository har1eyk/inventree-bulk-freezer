from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.db import close_old_connections, connection
from django.middleware.csrf import get_token
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from part.models import Part
from stock.models import StockItem, StockLocation
from users.models import RuleSet, ApiToken

from inventree_bulk_plugin.api import BulkCreate, TemplateList
from inventree_bulk_plugin.freezer import freezer_box, Conflict, position_names


class FreezerTests(TestCase):
    def setUp(self):
        ContentType.objects.clear_cache()
        self.slot = StockLocation.objects.create(name="Slot")
        self.data = {"mode": "freezer_box", "parent_id": self.slot.pk, "box_name": "Box", "layout": "9x9"}
        self.user = User.objects.create_user(username="operator")
        group = Group.objects.create(name="Freezer operators")
        RuleSet.objects.update_or_create(group=group, name="stock_location", defaults={"can_view": True, "can_add": True})
        self.user.groups.add(group)
        self.admin = User.objects.create_superuser(username="admin", email="test@example.invalid", password="test-only")

    def post(self, data=None, *, user=None, create=False):
        request = APIRequestFactory().post("/bulkcreate?create=" + str(create).lower(), data or self.data, format="json")
        force_authenticate(request, user=user or self.admin)
        return BulkCreate.as_view()(request)

    def test_both_layouts_preview_create_retry(self):
        for layout, count, last in [("9x9", 81, "I9"), ("10x10", 100, "J10")]:
            slot = StockLocation.objects.create(name=layout)
            data = {**self.data, "parent_id": slot.pk, "layout": layout}
            before = StockLocation.objects.count()
            preview = self.post(data)
            self.assertEqual(preview.status_code, 200)
            self.assertEqual(StockLocation.objects.count(), before)
            result = self.post(data, create=True)
            self.assertEqual(result.status_code, 201, result.data)
            box = StockLocation.objects.get(pk=result.data["box_id"])
            self.assertEqual(box.parent_id, slot.pk)
            self.assertEqual(box.children.count(), count)
            box.refresh_from_db()
            self.assertEqual(box.get_descendant_count(), count)
            self.assertEqual(set(box.get_descendants().values_list("name", flat=True)), set(position_names(layout)))
            self.assertTrue(all(p.pathstring == f"{box.pathstring}/{p.name}" for p in box.children.all()))
            self.assertEqual(result.data["positions"][-1], last)
            self.assertFalse(StockItem.objects.filter(location__parent=box).exists())
            again = self.post(data, create=True)
            self.assertEqual(again.status_code, 200)
            self.assertEqual(again.data["status"], "already_exists")
            self.assertEqual(StockLocation.objects.count(), before + count + 1)

    def test_occupied_stock_or_children_and_changed_layout(self):
        StockLocation.objects.create(name="Other box", parent=self.slot)
        self.assertEqual(self.post(create=True).status_code, 409)
        self.slot.children.all().delete()
        part = Part.objects.create(name="Sample")
        stock = StockItem.objects.create(part=part, quantity=1, location=self.slot)
        self.assertEqual(self.post(create=True).status_code, 409)
        stock.delete()
        self.assertEqual(self.post(create=True).status_code, 201)
        self.assertEqual(self.post({**self.data, "layout": "10x10"}, create=True).status_code, 409)

    def test_nested_or_partial_existing_box_is_not_repaired(self):
        result = freezer_box(self.data, create=True)
        box = StockLocation.objects.get(pk=result["box_id"])
        box.children.get(name="I9").delete()
        self.assertEqual(self.post(create=True).status_code, 409)
        self.assertEqual(box.children.count(), 80)

    def test_retry_preserves_stock(self):
        result = freezer_box(self.data, create=True)
        position = StockLocation.objects.get(parent_id=result["box_id"], name="A1")
        item = StockItem.objects.create(part=Part.objects.create(name="Sample"), quantity=1, location=position)
        self.assertEqual(self.post(create=True).data["status"], "already_exists")
        item.refresh_from_db()
        self.assertEqual(item.location_id, position.pk)

    def test_invalid_input(self):
        for change in [{"layout": "8x12"}, {"box_name": ""}, {"box_name": "a/b"}, {"parent_id": 0}]:
            self.assertEqual(self.post({**self.data, **change}, create=True).status_code, 400)
        self.assertEqual(self.post({**self.data, "parent_id": 9999999}, create=True).status_code, 404)
        self.assertEqual(self.slot.children.count(), 0)

    def test_transaction_rolls_back_on_position_failure(self):
        original = StockLocation.save
        def failing_save(instance, *args, **kwargs):
            if instance.name == "B2":
                raise RuntimeError("injected failure")
            return original(instance, *args, **kwargs)
        with patch.object(StockLocation, "save", failing_save):
            with self.assertRaises(RuntimeError):
                freezer_box(self.data, create=True)
        self.assertEqual(self.slot.children.count(), 0)
        self.assertFalse(StockLocation.objects.filter(name="A1").exists())

    def test_native_stock_role_and_denied_users(self):
        self.assertEqual(self.post(user=self.user, create=True).status_code, 201)
        denied = User.objects.create_user(username="denied")
        self.assertEqual(self.post(user=denied, create=True).status_code, 403)
        request = APIRequestFactory().post("/bulkcreate", self.data, format="json")
        self.assertIn(BulkCreate.as_view()(request).status_code, (401, 403))

    def test_csrf_session_enforced_and_valid_token_works(self):
        factory = APIRequestFactory(enforce_csrf_checks=True)
        request = factory.post("/bulkcreate", self.data, format="json")
        request.user = self.admin
        self.assertEqual(BulkCreate.as_view()(request).status_code, 403)
        request = factory.post("/bulkcreate", self.data, format="json")
        request.user = self.admin
        request.META["HTTP_X_CSRFTOKEN"] = get_token(request)
        request.COOKIES["csrftoken"] = request.META["CSRF_COOKIE"]
        self.assertEqual(BulkCreate.as_view()(request).status_code, 200)

    def test_template_writes_and_generic_generation_require_admin(self):
        request = APIRequestFactory().post("/templates", {"name": "test"}, format="json")
        force_authenticate(request, user=self.user)
        self.assertEqual(TemplateList.as_view()(request).status_code, 403)
        response = self.post({"template_type": "STOCK_LOCATION", "template": {}}, user=self.user, create=True)
        self.assertEqual(response.status_code, 403)

    def test_native_tokens_accept_valid_reject_revoked_and_expired(self):
        import datetime
        token = ApiToken.objects.create(user=self.admin, name="freezer test")
        def call():
            request = APIRequestFactory().post("/bulkcreate", self.data, format="json", HTTP_AUTHORIZATION="Token " + token.key)
            return BulkCreate.as_view()(request)
        self.assertEqual(call().status_code, 200)
        token.revoked = True
        token.save()
        self.assertEqual(call().status_code, 401)
        token.revoked = False
        token.expiry = datetime.date.today() - datetime.timedelta(days=1)
        token.save()
        self.assertEqual(call().status_code, 401)

    def test_portable_templates_match_layouts(self):
        import json
        from pathlib import Path
        from inventree_bulk_plugin.BulkGenerator.BulkGenerator import BulkGenerator
        from inventree_bulk_plugin.bulkcreate_objects import StockLocationBulkCreateObject
        root = Path(__file__).resolve().parents[2] / "freezer_templates"
        for layout in ("9x9", "10x10"):
            template = json.loads((root / f"freezer-{layout}.json").read_text())
            result = BulkGenerator(template["template"], fields=StockLocationBulkCreateObject.fields).generate({})
            self.assertEqual(len(result), 1)
            self.assertEqual([p[0]["name"] for p in result[0][1]], position_names(layout))


class FreezerConcurrencyTests(TransactionTestCase):
    def test_concurrent_slots_in_same_tree(self):
        if connection.vendor != "postgresql":
            self.skipTest("Row-lock acceptance test requires PostgreSQL")
        root = StockLocation.objects.create(name="Shared rack")
        slots = [StockLocation.objects.create(name=f"Slot {i}", parent=root) for i in range(2)]
        barrier = Barrier(2)
        def worker(slot_id):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return freezer_box({"parent_id": slot_id, "box_name": "Box", "layout": "9x9"}, create=True)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [s.pk for s in slots]))
        self.assertEqual([r["status"] for r in results], ["created", "created"])
        root.refresh_from_db()
        self.assertEqual(root.get_descendant_count(), 166)
        self.assertEqual(root.get_descendants().count(), 166)
        for slot in slots:
            slot.refresh_from_db()
            self.assertEqual(slot.get_descendant_count(), 82)
            box = slot.children.get()
            self.assertEqual(set(box.children.values_list("name", flat=True)), set(position_names("9x9")))

    def test_concurrent_same_and_different_box_requests(self):
        if connection.vendor != "postgresql":
            self.skipTest("Row-lock acceptance test requires PostgreSQL")
        for names in [("Same", "Same"), ("First", "Second")]:
            slot = StockLocation.objects.create(name="Concurrent " + names[0])
            barrier = Barrier(2)
            def worker(name):
                close_old_connections()
                try:
                    barrier.wait(timeout=10)
                    try:
                        return freezer_box({**{"mode": "freezer_box", "layout": "9x9"}, "parent_id": slot.pk, "box_name": name}, create=True)["status"]
                    except Conflict:
                        return "conflict"
                finally:
                    close_old_connections()
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(worker, names))
            self.assertEqual(results.count("created"), 1)
            self.assertIn("already_exists" if names[0] == names[1] else "conflict", results)
            self.assertEqual(slot.children.count(), 1)
            self.assertEqual(slot.children.first().children.count(), 81)
