
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from bookings.models import Booking
from hotels.models import Room


@transaction.atomic
def create_booking(*, user, validated_data):
    room = get_object_or_404(
        Room.objects.select_for_update(),
        pk=validated_data["room"].pk,
    )

    check_in = validated_data["check_in"]
    check_out = validated_data["check_out"]
    guests = validated_data["guests"]

    if not room.is_available:
        raise ValidationError({
            "room": "Этот номер сейчас недоступен для бронирования."
        })

    if guests > room.capacity:
        raise ValidationError({
            "guests": f"Вместимость этого номера — {room.capacity} гостей."
        })

    overlapping_bookings = Booking.objects.filter(
        room=room,
        check_in__lt=check_out,
        check_out__gt=check_in,
        status__in=[
            Booking.Status.PENDING,
            Booking.Status.CONFIRMED,
        ],
    )

    if overlapping_bookings.exists():
        raise ValidationError({
            "room": "Этот номер уже забронирован на выбранные даты."
        })

    nights = (check_out - check_in).days
    price_per_night = room.price_per_night
    total_price = price_per_night * nights

    return Booking.objects.create(
        user=user,
        room=room,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        price_per_night=price_per_night,
        total_price=total_price,
    )
