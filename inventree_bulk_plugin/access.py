"""Use the same role checks as native InvenTree endpoints."""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS
from users.permissions import check_user_permission


class AdminTemplateWrites(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff or request.user.is_superuser


def require_model_permission(user, model, action):
    if not check_user_permission(user, model, action):
        raise PermissionDenied(f"Requires {action} permission for {model._meta.verbose_name}.")
