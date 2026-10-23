from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Booking
from .permissions import BookingPermission
from .serializers import BookingSerializer
from .services import BookingError, create_booking


class BookingViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.RetrieveModelMixin,
):
    serializer_class = BookingSerializer
    permission_classes = [BookingPermission]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()

        user = self.request.user

        if user.role == 'admin':
            return Booking.objects.select_related(
                'user',
                'room',
                'room__hotel',
            ).order_by('-created_at')

        if user.role == 'hotel_manager':
            return Booking.objects.filter(
                room__hotel__manager=user,
            ).select_related(
                'user',
                'room',
                'room__hotel',
            ).order_by('-created_at')

        return Booking.objects.filter(
            user=user,
        ).select_related(
            'room',
            'room__hotel',
        ).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking = create_booking(
                user=request.user,
                validated_data=serializer.validated_data,
            )
        except BookingError as exc:
            detail = {exc.field: exc.message} if exc.field else {
                "detail": exc.message
            }

            return Response(
                detail,
                status=exc.status_code,
            )

        output_serializer = self.get_serializer(booking)

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.status == Booking.Status.CANCELLED:
            return Response(
                {'detail': 'Бронирование уже отменено.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status'])

        return Response(
            self.get_serializer(booking).data,
            status=status.HTTP_200_OK,
        )