from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Exists, OuterRef, Subquery
from django.utils.dateparse import parse_date
from django.db import transaction
from hotels.models import Room
from rest_framework.exceptions import ValidationError

from .models import Hotel, Room
from bookings.models import Booking
from .permissions import IsHotelManagerOrReadOnly
from .serializers import HotelSerializer, RoomSerializer


class HotelViewSet(viewsets.ModelViewSet):
    serializer_class = HotelSerializer
    permission_classes = [IsHotelManagerOrReadOnly]
    search_fields = ['name', 'country', 'city', 'address']
    ordering_fields = ['name', 'stars', 'created_at', 'price']


    def get_queryset(self):
        queryset = Hotel.objects.all().order_by('id')
        if self.action != 'list':
            return queryset
        params = self.request.query_params

        city = params.get('city')
        country = params.get('country')
        stars = params.get('stars')
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        guests = params.get('guests')

        check_in = parse_date(params.get('check_in', ''))
        check_out = parse_date(params.get('check_out', ''))

        if city:
            queryset = queryset.filter(city__iexact=city)

        if country:
            queryset = queryset.filter(country__iexact=country)

        if stars:
            queryset = queryset.filter(stars=stars)

        # Проверяем, что существует один номер,
        # который соответствует всем условиям поиска.
        rooms = Room.objects.filter(
            hotel_id=OuterRef('pk'),
            is_available=True,
        )

        if min_price:
            rooms = rooms.filter(price_per_night__gte=min_price)

        if max_price:
            rooms = rooms.filter(price_per_night__lte=max_price)

        if guests:
            rooms = rooms.filter(capacity__gte=guests)

        if check_in and check_out and check_out > check_in:
            overlapping_bookings = Booking.objects.filter(
                room_id=OuterRef('pk'),
                check_in__lt=check_out,
                check_out__gt=check_in,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                ],
            )

            rooms = rooms.annotate(
                has_booking=Exists(overlapping_bookings)
            ).filter(has_booking=False)



        queryset = queryset.annotate(
            has_matching_room=Exists(rooms),
            price=Subquery(
                rooms.order_by('price_per_night').values('price_per_night')[:1]
            )
        ).filter(
            has_matching_room=True
        )

        return queryset



    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

    @action(detail=True, methods=['post'], url_path='rooms')
    def rooms(self, request, pk=None):
        hotel = self.get_object()

        if (
            request.user.role != "admin"
            and hotel.manager != request.user
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'You can only add rooms to your own hotels.'
            )

        serializer = RoomSerializer(
            data={**request.data, 'hotel': hotel.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(hotel=hotel)

        return Response(serializer.data, status=201)



class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsHotelManagerOrReadOnly]
    filterset_fields = ['hotel', 'room_type', 'capacity', 'is_available']
    search_fields = ['room_number', 'hotel__name']
    ordering_fields = ['price_per_night', 'capacity']

    def get_queryset(self):
        return Room.objects.select_related('hotel').all().order_by('id')

    def perform_create(self, serializer):
        hotel = serializer.validated_data['hotel']

        if (
            self.request.user.role != "admin"
            and hotel.manager != self.request.user
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                'You can only add rooms to your own hotels.'
            )

        serializer.save()
