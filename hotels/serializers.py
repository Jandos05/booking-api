from rest_framework import serializers

from .models import Hotel, Room


class HotelSerializer(serializers.ModelSerializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)

    class Meta:
        model = Hotel
        fields = [
            'id',
            'manager',
            'name',
            'description',
            'country',
            'city',
            'address',
            'stars',
            'created_at',
        ]
        read_only_fields = ['id', 'manager', 'created_at']


class RoomSerializer(serializers.ModelSerializer):
    capacity = serializers.IntegerField(min_value=1)
    price_per_night = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
    )

    class Meta:
        model = Room
        fields = [
            'id',
            'hotel',
            'room_type',
            'room_number',
            'capacity',
            'price_per_night',
            'description',
            'is_available',
        ]
        read_only_fields = ['id']