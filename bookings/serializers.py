
from rest_framework import serializers
from django.utils import timezone
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            'id',
            'user',
            'room',
            'check_in',
            'check_out',
            'guests',
            'price_per_night',
            'total_price',
            'status',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'price_per_night',
            'total_price',
            'status',
            'created_at',
        ]


    def validate(self, attrs):
        check_in = attrs.get('check_in')
        check_out = attrs.get('check_out')
        guests = attrs.get('guests')
        room = attrs.get('room')

        if check_in and check_in < timezone.localdate():
            raise serializers.ValidationError({
                'check_in': 'Дата заезда не может быть в прошлом.'
            })

        if check_in and check_out and check_out <= check_in:
            raise serializers.ValidationError({
                'check_out': 'Дата выезда должна быть позже даты заезда.'
            })

        if guests is not None and guests < 1:
            raise serializers.ValidationError({
                'guests': 'Количество гостей должно быть не меньше 1.'
            })

        if room and guests is not None and guests > room.capacity:
            raise serializers.ValidationError({
                'guests': f'Вместимость этого номера — {room.capacity} гостей.'
            })

        if room and not room.is_available:
            raise serializers.ValidationError({
                'room': 'Этот номер сейчас недоступен для бронирования.'
            })


        if room and check_in and check_out:
            overlapping_bookings = Booking.objects.filter(
                room=room,
                check_in__lt=check_out,
                check_out__gt=check_in,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                ],
            )

            if self.instance:
                overlapping_bookings = overlapping_bookings.exclude(
                    pk=self.instance.pk
                )

            if overlapping_bookings.exists():
                raise serializers.ValidationError({
                    'room': 'Этот номер уже забронирован на выбранные даты.'
                })

        return attrs


    def create(self, validated_data):
        room = validated_data['room']
        check_in = validated_data['check_in']
        check_out = validated_data['check_out']

        nights = (check_out - check_in).days
        price_per_night = room.price_per_night
        total_price = price_per_night * nights

        return Booking.objects.create(
            **validated_data,
            price_per_night=price_per_night,
            total_price=total_price,
        )
