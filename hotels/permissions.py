
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsHotelManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        return request.user.role in ("hotel_manager", "admin")

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if not request.user.is_authenticated:
            return False

        if request.user.role == "admin":
            return True

        if request.user.role != "hotel_manager":
            return False

        if hasattr(obj, "manager"):
            return obj.manager == request.user

        if hasattr(obj, "hotel"):
            return obj.hotel.manager == request.user

        return False
