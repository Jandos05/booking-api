from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from bookings.models import Booking
from hotels.models import Hotel, Room

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
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=3)

        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(check_in),
                "check_out": str(check_out),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["price_per_night"], "2500.00")
        self.assertEqual(response.data["total_price"], "7500.00")
        self.assertEqual(response.data["status"], "pending")


    def test_booking_with_too_many_guests_is_rejected(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(check_in),
                "check_out": str(check_out),
                "guests": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )



    def test_overlapping_booking_is_rejected(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=3)

        first_response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(check_in),
                "check_out": str(check_out),
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
                "check_in": str(check_out - timedelta(days=1)),
                "check_out": str(check_out + timedelta(days=2)),
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

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=another_customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
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

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(check_in),
                "check_out": str(check_out),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )



    def test_customer_can_cancel_own_booking(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        booking = Booking.objects.create(
            user=self.customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
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


    def test_cancelled_booking_does_not_block_new_booking(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=self.customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=self.room.price_per_night,
            total_price=self.room.price_per_night * 2,
            status=Booking.Status.CANCELLED,
        )

        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(check_in),
                "check_out": str(check_out),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_customer_cannot_cancel_another_customers_booking(self):
        other_customer = User.objects.create_user(
            username="other_customer",
            password="testpass123",
        )

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        booking = Booking.objects.create(
            user=other_customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=2500,
            total_price=5000,
        )

        response = self.client.post(
            f"/api/bookings/{booking.id}/cancel/"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_manager_sees_only_bookings_for_own_hotels(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=self.customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=2500,
            total_price=5000,
        )

        another_manager = User.objects.create_user(
            username="another_manager",
            password="testpass123",
        )

        another_hotel = Hotel.objects.create(
            manager= another_manager,
            name="Another Hotel",
            description="Another hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Another address",
            stars=3,
        )


        another_room = Room.objects.create(
            hotel=another_hotel,
            room_type="double",
            room_number="201",
            capacity=2,
            price_per_night=3000,
            description="Another room",
            is_available=True,
        )

        Booking.objects.create(
            user=self.customer,
            room=another_room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=3000,
            total_price=6000,
        )

        self.client.force_authenticate(user=self.manager)

        response = self.client.get("/api/bookings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)


    def test_booking_with_invalid_room_id_returns_400(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        response = self.client.post(
            "/api/bookings/",
            {
                "room": "abc",
                "check_in": str(check_in),
                "check_out": str(check_out),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)



    def test_booking_with_invalid_check_in_date_returns_400(self):
        check_out = timezone.localdate() + timedelta(days=12)

        response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": "abc",
                "check_out": str(check_out),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)



    def test_booking_with_array_body_returns_400(self):
        response = self.client.post(
            "/api/bookings/",
            [
                {
                    "room": self.room.id,
                    "check_in": str(
                        timezone.localdate() + timedelta(days=10)
                    ),
                    "check_out": str(
                        timezone.localdate() + timedelta(days=12)
                    ),
                    "guests": 2,
                }
            ],
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)


    def test_booking_cannot_be_updated_or_deleted_directly(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        booking = Booking.objects.create(
            user=self.customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=self.room.price_per_night,
            total_price=self.room.price_per_night * 2,
        )

        url = f"/api/bookings/{booking.id}/"

        patch_response = self.client.patch(
            url,
            {"check_in": str(check_in + timedelta(days=1))},
            format="json",
        )
        delete_response = self.client.delete(url)

        self.assertEqual(
            patch_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            delete_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

        booking.refresh_from_db()
        self.assertEqual(booking.check_in, check_in)




    def test_manager_sees_bookings_for_own_hotel(self):
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=self.customer,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=self.room.price_per_night,
            total_price=self.room.price_per_night * 2,
        )

        self.client.force_authenticate(user=self.manager)
        response = self.client.get("/api/bookings/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)



    def test_adjacent_bookings_are_allowed(self):
        check_in = timezone.localdate() + timedelta(days=10)
        middle_date = check_in + timedelta(days=2)
        second_check_out = middle_date + timedelta(days=2)

        first_response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(check_in),
                "check_out": str(middle_date),
                "guests": 2,
            },
            format="json",
        )

        second_response = self.client.post(
            "/api/bookings/",
            {
                "room": self.room.id,
                "check_in": str(middle_date),
                "check_out": str(second_check_out),
                "guests": 2,
            },
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_booking_with_array_payload_returns_400(self):
        response = self.client.post(
            "/api/bookings/",
            [
                {
                    "room": self.room.id,
                    "check_in": str(
                        timezone.localdate() + timedelta(days=10)
                    ),
                    "check_out": str(
                        timezone.localdate() + timedelta(days=12)
                    ),
                    "guests": 2,
                }
            ],
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(Booking.objects.count(), 0)



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


    def test_database_rejects_overlapping_active_bookings(self):
        check_in = timezone.localdate() + timedelta(days=20)
        check_out = check_in + timedelta(days=3)

        Booking.objects.create(
            user=self.customer1,
            room=self.room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night=2500,
            total_price=7500,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Booking.objects.create(
                user=self.customer2,
                room=self.room,
                check_in=check_in + timedelta(days=1),
                check_out=check_out + timedelta(days=1),
                guests=2,
                price_per_night=2500,
                total_price=7500,
            )

        self.assertEqual(
            Booking.objects.filter(room=self.room).count(),
            1,
        )





    def test_concurrent_overlapping_bookings_create_at_most_one(self):
        barrier = Barrier(2)
        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=3)

        def create_booking(user_id):
            from django.db import close_old_connections

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
                        "check_in": check_in.isoformat(),
                        "check_out": check_out.isoformat(),
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
                check_in=check_in,
                check_out=check_out,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.CONFIRMED,
                ],
            ).count(),
            1,
        )