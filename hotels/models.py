from django.conf import settings
from django.db import models


class Hotel(models.Model):
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='managed_hotels',
        limit_choices_to={'role': 'hotel_manager'},
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    stars = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stars__gte=1, stars__lte=5),
                name='hotel_stars_between_1_and_5',
            ),
        ]

    def __str__(self):
        return self.name



class Room(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = 'single', 'Single'
        DOUBLE = 'double', 'Double'
        TWIN = 'twin', 'Twin'
        FAMILY = 'family', 'Family'
        SUITE = 'suite', 'Suite'

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='rooms',
    )
    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.DOUBLE,
    )
    room_number = models.CharField(max_length=20)
    capacity = models.PositiveSmallIntegerField(default=2)
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    description = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['hotel', 'room_number'],
                name='unique_room_number_per_hotel',
            ),

            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name='room_capacity_at_least_one',
            ),
            models.CheckConstraint(
                condition=models.Q(price_per_night__gte=0),
                name='room_price_non_negative',
            ),
        ]

    def __str__(self):
        return f'{self.hotel.name} — {self.room_number}'

