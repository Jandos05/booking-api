
from django.db import transaction

from bookings.models import Booking
from hotels.models import Room


class BookingError(Exception):
    def __init__(self, message, field=None, status_code=400):
        self.message = message
        self.field = field
        self.status_code = status_code
        super().__init__(message)


@transaction.atomic
def create_booking(*, user, validated_data):
    room = Room.objects.select_for_update().filter(
        pk=validated_data["room"].pk,
    ).first()

    if room is None:
        raise BookingError(
            "Номер не найден.",
            field="room",
            status_code=400,
        )

    check_in = validated_data["check_in"]
    check_out = validated_data["check_out"]
    guests = validated_data["guests"]

    if not room.is_available:
        raise BookingError(
            "Этот номер сейчас недоступен для бронирования.",
            field="room",
        )

    if guests > room.capacity:
        raise BookingError(
            f"Вместимость этого номера — {room.capacity} гостей.",
            field="guests",
        )

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
        raise BookingError(
            "Этот номер уже забронирован на выбранные даты.",
            field="room",
        )

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
