from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from bookings.models import Booking
from hotels.models import Hotel, Room

User = get_user_model()


class HotelAPITests(APITestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            username="test_manager",
            password="test_password123",
            role="hotel_manager",
        )

        self.other_manager = User.objects.create_user(
            username="other_manager",
            password="test_password123",
            role="hotel_manager",
        )

        self.hotel = Hotel.objects.create(
            manager=self.other_manager,
            name="Other Hotel",
            description="Another manager's hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Test address",
            stars=4,
        )

        self.client.force_authenticate(user=self.manager)

    def test_hotel_cannot_be_created_with_more_than_five_stars(self):
        response = self.client.post(
            "/api/hotels/",
            {
                "name": "Invalid Hotel",
                "description": "Hotel with invalid stars",
                "country": "Kyrgyzstan",
                "city": "Bishkek",
                "address": "Test address",
                "stars": 6,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Hotel.objects.filter(name="Invalid Hotel").exists())
    def test_manager_can_create_own_hotel(self):
        response = self.client.post(
            "/api/hotels/",
            {
                "name": "My Hotel",
                "description": "My first hotel",
                "country": "Kyrgyzstan",
                "city": "Bishkek",
                "address": "Test address 2",
                "stars": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["manager"], self.manager.id)

    def test_admin_can_update_another_managers_hotel(self):
        admin = User.objects.create_user(
            username="test_admin",
            password="test_password123",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin)

        response = self.client.patch(
            f"/api/hotels/{self.hotel.id}/",
            {"name": "Updated by Admin"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.name, "Updated by Admin")

    def test_manager_cannot_update_another_managers_hotel(self):
        response = self.client.patch(
            f"/api/hotels/{self.hotel.id}/",
            {"name": "Hacked Hotel"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.name, "Other Hotel")

    def test_manager_cannot_add_room_to_another_managers_hotel(self):
        response = self.client.post(
            "/api/rooms/",
            {
                "hotel": self.hotel.id,
                "room_type": "double",
                "room_number": "202",
                "capacity": 2,
                "price_per_night": "3000.00",
                "description": "Test room",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            self.hotel.rooms.filter(room_number="202").exists()
        )

    def test_manager_cannot_move_room_to_another_managers_hotel(self):
        own_hotel = Hotel.objects.create(
            manager=self.manager,
            name="My Hotel",
            description="My hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="My hotel address",
            stars=3,
        )

        room = Room.objects.create(
            hotel=own_hotel,
            room_type="double",
            room_number="501",
            capacity=2,
            price_per_night="3000.00",
            description="My room",
            is_available=True,
        )

        response = self.client.patch(
            f"/api/rooms/{room.id}/",
            {"hotel": self.hotel.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        room.refresh_from_db()
        self.assertEqual(room.hotel_id, own_hotel.id)

    def test_manager_cannot_take_another_managers_room(self):
        own_hotel = Hotel.objects.create(
            manager=self.manager,
            name="My Hotel",
            description="My hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="My hotel address",
            stars=3,
        )

        foreign_room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="601",
            capacity=2,
            price_per_night="3000.00",
            description="Foreign room",
            is_available=True,
        )

        response = self.client.patch(
            f"/api/rooms/{foreign_room.id}/",
            {"hotel": own_hotel.id},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        foreign_room.refresh_from_db()
        self.assertEqual(foreign_room.hotel_id, self.hotel.id)


    def test_manager_can_add_room_to_own_hotel_through_nested_endpoint(self):
        own_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Nested Hotel",
            description="Hotel for nested room test",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Nested hotel address",
            stars=3,
        )

        response = self.client.post(
            f"/api/hotels/{own_hotel.id}/rooms/",
            {
                "room_type": "double",
                "room_number": "301",
                "capacity": 2,
                "price_per_night": "2500.00",
                "description": "Room created through nested endpoint",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=str(response.data),
        )
        self.assertEqual(response.data["hotel"], own_hotel.id)
        self.assertTrue(
            own_hotel.rooms.filter(room_number="301").exists()
        )



    def test_manager_can_add_room_through_nested_endpoint_with_form_data(self):
        own_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Form Data Hotel",
            description="Hotel for form-data test",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Form data address",
            stars=3,
        )

        response = self.client.post(
            f"/api/hotels/{own_hotel.id}/rooms/",
            {
                "room_type": "double",
                "room_number": "302",
                "capacity": 2,
                "price_per_night": "3000.00",
                "description": "Room created with form data",
                "is_available": "true",
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=str(response.data),
        )
        self.assertEqual(response.data["hotel"], own_hotel.id)
        self.assertTrue(
            own_hotel.rooms.filter(room_number="302").exists()
        )




    def test_hotel_search_by_city_is_case_insensitive(self):
        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="101",
            capacity=2,
            price_per_night="3000.00",
            description="Test room",
            is_available=True,
        )

        response = self.client.get("/api/hotels/?city=bIsHkEk")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            self.hotel.id,
        )




    def test_hotel_search_filters_by_price_and_guests(self):
        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="102",
            capacity=2,
            price_per_night="3000.00",
            description="Affordable room",
            is_available=True,
        )

        Room.objects.create(
            hotel=self.hotel,
            room_type="family",
            room_number="103",
            capacity=4,
            price_per_night="6000.00",
            description="Family room",
            is_available=True,
        )

        response = self.client.get(
            "/api/hotels/?min_price=2500&max_price=4000&guests=2"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.hotel.id)



    def test_hotel_search_excludes_fully_booked_room(self):
        from datetime import timedelta

        from bookings.models import Booking

        room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="104",
            capacity=2,
            price_per_night="3000.00",
            description="Booked room",
            is_available=True,
        )

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=self.manager,
            room=room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night="3000.00",
            total_price="6000.00",
            status=Booking.Status.CONFIRMED,
        )

        response = self.client.get(
            f"/api/hotels/?check_in={check_in.isoformat()}"
            f"&check_out={check_out.isoformat()}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)


    def test_hotel_search_includes_room_with_cancelled_booking(self):
        room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="109",
            capacity=2,
            price_per_night="3000.00",
            description="Room with cancelled booking",
            is_available=True,
        )

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=self.manager,
            room=room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night="3000.00",
            total_price="6000.00",
            status=Booking.Status.CANCELLED,
        )

        response = self.client.get(
            f"/api/hotels/?check_in={check_in.isoformat()}"
            f"&check_out={check_out.isoformat()}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.hotel.id)



    def test_hotel_search_includes_hotel_if_another_room_is_free(self):
        from datetime import timedelta

        from bookings.models import Booking

        booked_room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="105",
            capacity=2,
            price_per_night="3000.00",
            description="Booked room",
            is_available=True,
        )

        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="106",
            capacity=2,
            price_per_night="3500.00",
            description="Free room",
            is_available=True,
        )

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=self.manager,
            room=booked_room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night="3000.00",
            total_price="6000.00",
            status=Booking.Status.CONFIRMED,
        )

        response = self.client.get(
            f"/api/hotels/?check_in={check_in.isoformat()}"
            f"&check_out={check_out.isoformat()}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.hotel.id)





    def test_hotel_search_can_order_by_price(self):
        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="107",
            capacity=2,
            price_per_night="5000.00",
            description="Expensive room",
            is_available=True,
        )

        cheaper_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Cheaper Hotel",
            description="Budget hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Another address",
            stars=3,
        )

        Room.objects.create(
            hotel=cheaper_hotel,
            room_type="double",
            room_number="201",
            capacity=2,
            price_per_night="2000.00",
            description="Cheap room",
            is_available=True,
        )

        response = self.client.get("/api/hotels/?ordering=price")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            response.data["results"][0]["id"],
            cheaper_hotel.id,
        )
        self.assertEqual(
            response.data["results"][1]["id"],
            self.hotel.id,
        )




    def test_hotel_search_can_order_by_price_descending(self):
        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="108",
            capacity=2,
            price_per_night="5000.00",
            description="Expensive room",
            is_available=True,
        )

        cheaper_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Cheaper Hotel",
            description="Budget hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Another address",
            stars=3,
        )

        Room.objects.create(
            hotel=cheaper_hotel,
            room_type="double",
            room_number="202",
            capacity=2,
            price_per_night="2000.00",
            description="Cheap room",
            is_available=True,
        )

        response = self.client.get("/api/hotels/?ordering=-price")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["id"], self.hotel.id)
        self.assertEqual(
            response.data["results"][1]["id"],
            cheaper_hotel.id,
        )

    def test_hotel_list_pagination(self):
        for i in range(11):
            hotel = Hotel.objects.create(
                manager=self.manager,
                name=f"Pagination Hotel {i}",
                description="Hotel for pagination test",
                country="Kyrgyzstan",
                city="Bishkek",
                address=f"Address {i}",
                stars=3,
            )
            Room.objects.create(
                hotel=hotel,
                room_type="double",
                room_number=f"P{i}",
                capacity=2,
                price_per_night="3000.00",
                description="Test room",
                is_available=True,
            )

        first_page = self.client.get("/api/hotels/")

        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data["count"], 11)
        self.assertEqual(len(first_page.data["results"]), 10)
        self.assertIsNotNone(first_page.data["next"])

        second_page = self.client.get("/api/hotels/?page=2")

        self.assertEqual(second_page.status_code, status.HTTP_200_OK)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertIsNone(second_page.data["next"])

    def test_hotel_search_can_order_by_stars(self):
        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="109",
            capacity=2,
            price_per_night="3000.00",
            description="Test room",
            is_available=True,
        )

        higher_rated_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Five Star Hotel",
            description="Higher rated hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Higher rated address",
            stars=5,
        )

        Room.objects.create(
            hotel=higher_rated_hotel,
            room_type="double",
            room_number="203",
            capacity=2,
            price_per_night="3000.00",
            description="Test room",
            is_available=True,
        )

        response = self.client.get("/api/hotels/?ordering=-stars")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            response.data["results"][0]["id"],
            higher_rated_hotel.id,
        )
        self.assertEqual(
            response.data["results"][1]["id"],
            self.hotel.id,
        )

    def test_admin_can_add_room_to_another_managers_hotel(self):
        admin = User.objects.create_user(
            username="room_test_admin",
            password="test_password123",
            role=User.Role.ADMIN,
        )
        self.client.force_authenticate(user=admin)

        response = self.client.post(
            "/api/rooms/",
            {
                "hotel": self.hotel.id,
                "room_type": "double",
                "room_number": "303",
                "capacity": 2,
                "price_per_night": "3500.00",
                "description": "Admin-created room",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            self.hotel.rooms.filter(room_number="303").exists()
        )

    def test_invalid_search_parameters_return_400(self):

        invalid_params = [
            "?guests=abc",
            "?guests=0",
            "?stars=abc",
            "?stars=7",
            "?min_price=abc",
            "?max_price=x",
            "?min_price=-100",
            "?max_price=-5",
            "?min_price=5000&max_price=1000",
            "?check_in=abc",
            "?check_in=2026-13-40",
            "?check_out=abc",
            "?ordering=bogus",
        ]


        for params in invalid_params:
            with self.subTest(params=params):
                response = self.client.get(
                    f"/api/hotels/{params}"
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                    msg=f"Параметры {params} должны возвращать 400",
                )


    def test_invalid_ordering_returns_400(self):
        response = self.client.get(
            "/api/hotels/?ordering=bogus"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


    def test_max_price_zero_is_applied(self):
        Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="110",
            capacity=2,
            price_per_night="3000.00",
            description="Paid room",
            is_available=True,
        )

        free_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Zero Price Hotel",
            description="Hotel with a zero-price room",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Zero price address",
            stars=3,
        )

        Room.objects.create(
            hotel=free_hotel,
            room_type="single",
            room_number="204",
            capacity=1,
            price_per_night="0.00",
            description="Zero-price room",
            is_available=True,
        )

        response = self.client.get(
            "/api/hotels/?max_price=0"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            free_hotel.id,
        )


    def test_room_with_booking_cannot_be_deleted(self):
        room = self._create_room_with_booking()

        response = self.client.delete(
            f"/api/rooms/{room.id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Room.objects.filter(id=room.id).exists())

    def test_hotel_with_booking_cannot_be_deleted(self):
        room = self._create_room_with_booking()
        hotel_id = room.hotel_id

        response = self.client.delete(
            f"/api/hotels/{hotel_id}/"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Hotel.objects.filter(id=hotel_id).exists())
        self.assertTrue(Room.objects.filter(id=room.id).exists())

    def _create_room_with_booking(self):
        hotel = Hotel.objects.create(
            manager=self.manager,
            name="Hotel With Booking",
            description="Test hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Test address",
            stars=3,
        )

        room = Room.objects.create(
            hotel=hotel,
            room_type="double",
            room_number="901",
            capacity=2,
            price_per_night="3000.00",
            description="Test room",
            is_available=True,
        )

        customer = User.objects.create_user(
            username="booking_customer",
            password="test_password123",
            role="customer",
        )

        check_in = timezone.localdate() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)

        Booking.objects.create(
            user=customer,
            room=room,
            check_in=check_in,
            check_out=check_out,
            guests=2,
            price_per_night="3000.00",
            total_price="6000.00",
        )

        return room


    def test_room_number_must_be_unique_within_hotel(self):
        own_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Unique Room Hotel",
            description="Test hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Unique room address",
            stars=3,
        )

        Room.objects.create(
            hotel=own_hotel,
            room_type="double",
            room_number="101",
            capacity=2,
            price_per_night="3000.00",
        )

        with self.assertRaises(IntegrityError):
            Room.objects.create(
                hotel=own_hotel,
                room_type="single",
                room_number="101",
                capacity=1,
                price_per_night="2000.00",
            )

    def test_same_room_number_is_allowed_in_different_hotels(self):
        first_hotel = Hotel.objects.create(
            manager=self.manager,
            name="First Hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="First address",
            stars=3,
        )

        second_hotel = Hotel.objects.create(
            manager=self.manager,
            name="Second Hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="Second address",
            stars=3,
        )

        Room.objects.create(
            hotel=first_hotel,
            room_type="double",
            room_number="101",
            capacity=2,
            price_per_night="3000.00",
        )

        room = Room.objects.create(
            hotel=second_hotel,
            room_type="double",
            room_number="101",
            capacity=2,
            price_per_night="3000.00",
        )

        self.assertIsNotNone(room.pk)

    def test_manager_cannot_delete_another_managers_room(self):
        foreign_room = Room.objects.create(
            hotel=self.hotel,
            room_type="double",
            room_number="602",
            capacity=2,
            price_per_night="3000.00",
            description="Foreign room",
            is_available=True,
        )

        response = self.client.delete(
            f"/api/rooms/{foreign_room.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Room.objects.filter(pk=foreign_room.pk).exists()
        )

    def test_manager_cannot_delete_another_managers_hotel(self):
        response = self.client.delete(
            f"/api/hotels/{self.hotel.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertTrue(
            Hotel.objects.filter(pk=self.hotel.pk).exists()
        )