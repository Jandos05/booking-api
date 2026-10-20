from django.db import transaction
from django.shortcuts import get_object_or_404

from hotels.models import Room


@transaction.atomic
def create_booking(*, user, serializer):
    room_id = serializer.initial_data.get("room")

    get_object_or_404(
        Room.objects.select_for_update(),
        pk=room_id,
    )

    serializer.is_valid(raise_exception=True)

    return serializer.save(user=user)
