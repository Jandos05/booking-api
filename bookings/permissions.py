
from rest_framework.permissions import BasePermission


class BookingPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [
                'admin',
                'hotel_manager',
                'customer',
            ]
        )

    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.role == 'admin':
            return True

        if user.role == 'hotel_manager':
            return obj.room.hotel.manager == user

        if user.role == 'customer':
            if view.action == 'cancel':
                return obj.user == user

            return obj.user == user and request.method in [
                'GET',
                'HEAD',
                'OPTIONS',
            ]

        return False
