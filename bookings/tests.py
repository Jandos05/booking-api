
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.test import TransactionTestCase
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from hotels.models import Hotel, Room
from bookings.models import Booking


User = get_user_model()


class BookingAPITests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="test_customer",
            password="test_password123",
            role="customer",
        )

        self.manager = User.objects.create_user(
            username="test_manager",
            password="test_password123",
            role="hotel_manager",
        )

        self.hotel = Hotel.objects.create(
            manager=self.manager,
            name="Test Hotel",
            description="Hotel for automated tests",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Test address",
            stars=4,
        )

        self.room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="101",
            capacity=2,
            price_per_night=2500,
            description="Test room",
            is_available=True,
        )

        self.client.force_authenticate(user=self.customer)

    def test_create_booking_calculates_total_price(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "2026-11-10",
                "check_out": "2026-11-13",
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["price_per_night"], "2500.00")
        self.assertEqual(response.data["total_price"], "7500.00")
        self.assertEqual(response.data["status"], "pending")

    def test_booking_with_past_check_in_is_rejected(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "2020-01-01",
                "check_out": "2020-01-03",
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_booking_with_too_many_guests_is_rejected(self):
        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "2026-11-10",
                "check_out": "2026-11-12",
                "guests": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)



    def test_overlapping_booking_is_rejected(self):
        first_response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "2026-11-10",
                "check_out": "2026-11-13",
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "2026-11-12",
                "check_out": "2026-11-15",
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )



    def test_customer_sees_only_own_bookings(self):
        another_customer = User.objects.create_user(
            username="another_customer",
            password="test_password123",
            role="customer",
        )

        Booking.objects.create(
            user=another_customer,
            room=self.room,
            check_in=date(2026, 11, 10),
            check_out=date(2026, 11, 12),
            guests=2,
            price_per_night=2500,
            total_price=5000,
        )

        response = self.client.get("/api/bookings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)




    def test_unavailable_room_cannot_be_booked(self):
        self.room.is_available = False
        self.room.save()

        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "2026-11-10",
                "check_out": "2026-11-12",
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )



    def test_customer_can_cancel_own_booking(self):
        booking = Booking.objects.create(
            user=self.customer,
            room=self.room,
            check_in=date(2026, 11, 10),
            check_out=date(2026, 11, 12),
            guests=2,
            price_per_night=2500,
            total_price=5000,
        )

        response = self.client.post(
            f"/api/bookings/{booking.id}/cancel/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)


    def test_customer_cannot_cancel_another_customers_booking(self):
        another_customer = User.objects.create_user(
            username="other_customer_cancel",
            password="test_password123",
            role="customer",
        )

        booking = Booking.objects.create(
            user=another_customer,
            room=self.room,
            check_in=date(2026, 11, 10),
            check_out=date(2026, 11, 12),
            guests=2,
            price_per_night=2500,
            total_price=5000,
        )

        response = self.client.post(
            f"/api/bookings/{booking.id}/cancel/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        booking.refresh_from_db()
        self.assertNotEqual(
            booking.status,
            Booking.Status.CANCELLED,
        )


    def test_manager_sees_only_bookings_for_own_hotels(self):
        another_manager = User.objects.create_user(
            username="another_manager",
            password="test_password123",
            role="hotel_manager",
        )

        another_hotel = Hotel.objects.create(
            manager=another_manager,
            name="Another Hotel",
            description="Another test hotel",
            country="Kyrgyzstan",
            city="Osh",
            address="Another address",
            stars=3,
        )

        another_room = Room.objects.create(
            hotel=another_hotel,
            room_type="single",
            room_number="201",
            capacity=1,
            price_per_night=1500,
            description="Another test room",
            is_available=True,
        )

        Booking.objects.create(
            user=self.customer,
            room=another_room,
            check_in=date(2026, 11, 10),
            check_out=date(2026, 11, 12),
            guests=1,
            price_per_night=1500,
            total_price=3000,
        )

        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/api/bookings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

class ConcurrentBookingTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.customer1 = User.objects.create_user(
            username="concurrent_customer1",
            password="test_password123",
            role="customer",
        )
        self.customer2 = User.objects.create_user(
            username="concurrent_customer2",
            password="test_password123",
            role="customer",
        )

        self.manager = User.objects.create_user(
            username="concurrent_manager",
            password="test_password123",
            role="hotel_manager",
        )

        self.hotel = Hotel.objects.create(
            manager=self.manager,
            name="Concurrent Test Hotel",
            description="Hotel for concurrency tests",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Test address",
            stars=4,
        )

        self.room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="201",
            capacity=2,
            price_per_night=2500,
            description="Room for concurrency tests",
            is_available=True,
        )

    def test_concurrent_overlapping_bookings_create_at_most_one(self):
        barrier = Barrier(2)

        def create_booking(user_id):
            from django.db import close_old_connections
            from rest_framework.test import APIClient

            close_old_connections()
            try:
                user = User.objects.get(pk=user_id)
                client = APIClient()
                client.force_authenticate(user=user)

                barrier.wait(timeout=10)

                return client.post(
                    "/api/bookings/",
                    {
                        "room": self.room.pk,
                        "check_in": "2026-11-10",
                        "check_out": "2026-11-13",
                        "guests": 2,
                    },
                    format="json",
                ).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                create_booking,
                [self.customer1.pk, self.customer2.pk],
            ))

        self.assertEqual(results.count(201), 1, results)
        self.assertEqual(
            Booking.objects.filter(
                room=self.room,
                check_in=date(2026, 11, 10),
                check_out=date(2026, 11, 13),
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                ],
            ).count(),
            1,
        )