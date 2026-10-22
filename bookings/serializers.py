
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

        return attrs
