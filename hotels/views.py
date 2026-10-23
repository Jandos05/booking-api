
from decimal import Decimal, InvalidOperation

from django.db.models import Exists, OuterRef, Subquery
from django.db.models.deletion import ProtectedError
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from bookings.models import Booking
from .models import Hotel, Room
from .permissions import IsHotelManagerOrReadOnly
from .serializers import HotelSerializer, RoomSerializer


class ConflictError(APIException):
    status_code = 409
    default_detail = 'Нельзя удалить объект, связанный с бронированиями.'
    default_code = 'conflict'

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

        ordering = params.get('ordering')

        if ordering is not None:
            allowed_fields = set(self.ordering_fields)
            ordering_terms = [
                field.strip() for field in ordering.split(',')
            ]

            invalid_fields = [
                field
                for field in ordering_terms
                if (
                    not field
                    or field == '-'
                    or field.startswith('--')
                    or (
                        field[1:]
                        if field.startswith('-')
                        else field
                    ) not in allowed_fields
                )
            ]

            if invalid_fields:
                raise ValidationError({
                    'ordering': (
                        'Недопустимое поле сортировки: '
                        + ', '.join(invalid_fields)
                    )
                })

        city = params.get('city')
        country = params.get('country')
        stars = params.get('stars')
        min_price = params.get('min_price')
        max_price = params.get('max_price')
        guests = params.get('guests')

        if stars is not None:
            try:
                stars = int(stars)
            except (TypeError, ValueError):
                raise ValidationError({
                    'stars': 'Укажите целое число от 1 до 5.'
                })

            if stars < 1 or stars > 5:
                raise ValidationError({
                    'stars': 'Количество звёзд должно быть от 1 до 5.'
                })

        if guests is not None:
            try:
                guests = int(guests)
            except (TypeError, ValueError):
                raise ValidationError({
                    'guests': 'Укажите целое положительное число.'
                })

            if guests < 1:
                raise ValidationError({
                    'guests': 'Количество гостей должно быть больше нуля.'
                })

        for param_name in ('min_price', 'max_price'):
            value = params.get(param_name)

            if value is not None:
                try:
                    price = Decimal(value)
                except (InvalidOperation, ValueError):
                    raise ValidationError({
                        param_name: 'Укажите корректную цену.'
                    })

                if not price.is_finite() or price < 0:
                    raise ValidationError({
                        param_name: (
                            'Цена должна быть конечным '
                            'неотрицательным числом.'
                        )
                    })

                if param_name == 'min_price':
                    min_price = price
                else:
                    max_price = price

        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            raise ValidationError({
                'max_price': 'Максимальная цена не может быть меньше минимальной.'
            })

        check_in_raw = params.get('check_in')
        check_out_raw = params.get('check_out')

        check_in = None
        check_out = None

        if check_in_raw is not None:
            try:
                check_in = parse_date(check_in_raw)
            except ValueError:
                check_in = None

            if check_in is None:
                raise ValidationError({
                    'check_in': 'Используйте формат даты YYYY-MM-DD.'
                })

        if check_out_raw is not None:
            try:
                check_out = parse_date(check_out_raw)
            except ValueError:
                check_out = None

            if check_out is None:
                raise ValidationError({
                    'check_out': 'Используйте формат даты YYYY-MM-DD.'
                })

        if (check_in is None) != (check_out is None):
            raise ValidationError(
                'Укажите обе даты: check_in и check_out.'
            )

        if check_in is not None and check_out <= check_in:
            raise ValidationError({
                'check_out': 'Дата выезда должна быть позже даты заезда.'
            })
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

        if min_price is not None:
            rooms = rooms.filter(price_per_night__gte=min_price)

        if max_price is not None:
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


    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            self.perform_destroy(instance)
        except ProtectedError:
            raise ConflictError()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

    @action(detail=True, methods=['post'], url_path='rooms')
    def rooms(self, request, pk=None):
        hotel = self.get_object()

        if (
                request.user.role != "admin"
                and hotel.manager != request.user
        ):

            raise PermissionDenied(
                'You can only add rooms to your own hotels.'
            )

        room_data = request.data.copy()
        room_data['hotel'] = hotel.id

        serializer = RoomSerializer(data=room_data)
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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            self.perform_destroy(instance)
        except ProtectedError:
            raise ConflictError()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        hotel = serializer.validated_data['hotel']

        if (
            self.request.user.role != "admin"
            and hotel.manager != self.request.user
        ):

            raise PermissionDenied(
                'You can only add rooms to your own hotels.'
            )

        serializer.save()


    def perform_update(self, serializer):
        hotel = serializer.validated_data.get(
            "hotel",
            serializer.instance.hotel,
        )

        if (
            self.request.user.role != "admin"
            and hotel.manager != self.request.user
        ):
            raise PermissionDenied(
                "You can only move rooms to your own hotels."
            )

        serializer.save()