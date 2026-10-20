from .services import create_booking
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import BookingPermission


from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
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
        booking = create_booking(
            user=request.user,
            serializer=serializer,
        )

        response_serializer = self.get_serializer(booking)
        headers = self.get_success_headers(response_serializer.data)

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
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