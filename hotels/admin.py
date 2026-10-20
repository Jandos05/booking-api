
from django.contrib import admin

from .models import Hotel, Room


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'city',
        'country',
        'stars',
        'manager',
    )
    list_filter = ('country', 'city', 'stars')
    search_fields = ('name', 'city', 'country')


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        'room_number',
        'hotel',
        'room_type',
        'capacity',
        'price_per_night',
        'is_available',
    )
    list_filter = ('room_type', 'capacity', 'is_available')
    search_fields = ('room_number', 'hotel__name')

