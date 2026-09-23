"""Atomic freezer-box creation using ordinary InvenTree stock locations."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound, ValidationError
from stock.models import StockItem, StockLocation


class Conflict(APIException):
    status_code = 409
    default_code = "occupied_slot"


class FreezerRequest(serializers.Serializer):
    parent_id = serializers.IntegerField(min_value=1)
    box_name = serializers.CharField(
        max_length=StockLocation._meta.get_field("name").max_length,
        trim_whitespace=True,
    )
    layout = serializers.ChoiceField(choices=["9x9", "10x10"], default="9x9")

    def validate_box_name(self, value):
        if any(ord(c) < 32 for c in value) or "/" in value or "\\" in value:
            raise serializers.ValidationError("Use a name without slashes or control characters.")
        return value


def position_names(layout):
    size = {"9x9": 9, "10x10": 10}[layout]
    return [f"{chr(65 + row)}{column}" for row in range(size) for column in range(1, size + 1)]


def inspect_slot(parent, name, names):
    if StockItem.objects.filter(location=parent).exists():
        raise Conflict("The selected rack slot contains stock.")
    children = list(StockLocation.objects.filter(parent=parent))
    if not children:
        return None
    if len(children) == 1 and children[0].name == name:
        box = children[0]
        positions = list(StockLocation.objects.filter(parent=box))
        exact = (
            not box.structural and not box.external
            and len(positions) == len(names)
            and {p.name for p in positions} == set(names)
            and all(not p.structural and not p.external for p in positions)
            and not StockLocation.objects.filter(parent__in=positions).exists()
        )
        if exact:
            return box
    raise Conflict("The selected rack slot is occupied or its existing box has a different layout.")


def freezer_box(data, *, create=False):
    serializer = FreezerRequest(data=data)
    serializer.is_valid(raise_exception=True)
    values = serializer.validated_data
    names = position_names(values["layout"])
    # Lock the parent before inspecting children: competing requests serialize here.
    with transaction.atomic():
        query = StockLocation.objects
        try:
            parent = query.get(pk=values["parent_id"])
            if create:
                # MPTT updates touch other nodes in the same tree. Lock the root
                # first so creation into different slots in a rack also serializes.
                query.select_for_update().get(pk=parent.get_root().pk)
                parent = query.select_for_update().get(pk=parent.pk)
        except StockLocation.DoesNotExist:
            raise NotFound("The selected rack slot no longer exists.")
        box = inspect_slot(parent, values["box_name"], names)
        result_status = "already_exists" if box else "ready"
        if create and not box:
            try:
                box = StockLocation(name=values["box_name"], parent=parent, structural=False, external=False)
                box.full_clean()
                box.save()
                for name in names:
                    position = StockLocation(name=name, parent=box, structural=False, external=False)
                    position.full_clean()
                    # Native save still performs MPTT insertion, validation,
                    # path generation, and signals. Defer only InvenTree's extra
                    # whole-tree rebuild, otherwise it runs 81/100 times per box.
                    # The override belongs to this new instance, never the class.
                    position.partial_rebuild = lambda tree_id: True
                    position.save()
                # Use the manager so a rebuild failure propagates and rolls back.
                StockLocation.objects.partial_rebuild(box.tree_id)
            except DjangoValidationError as exc:
                raise ValidationError(exc.messages)
            result_status = "created"
        return {
            "status": result_status,
            "parent_id": parent.pk,
            "parent_path": parent.pathstring,
            "box_name": values["box_name"],
            "layout": values["layout"],
            "position_count": len(names),
            "positions": names,
            "box_id": box.pk if box else None,
            "box_url": f"/web/stock/location/{box.pk}/" if box else None,
        }
