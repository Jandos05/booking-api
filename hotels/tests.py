from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

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

    def test_manager_can_add_room_to_own_hotel_through_nested_endpoint(self):
        own_hotel = Hotel.objects.create(
            manager=self.manager,
            name="My Hotel",
            description="My hotel",
            country="Kyrgyzstan",
            city="Bishkek",
            address="My hotel address",
            stars=3,
        )

        response = self.client.post(
            f"/api/hotels/{own_hotel.id}/rooms/",
            {
                "room_type": "double",
                "room_number": "301",
                "capacity": 2,
                "price_per_night": "3000.00",
                "description": "New room",
                "is_available": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["hotel"], own_hotel.id)
        self.assertTrue(
            own_hotel.rooms.filter(room_number="301").exists()
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
        from datetime import date, timedelta

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

        check_in = date.today() + timedelta(days=10)
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




    def test_hotel_search_includes_hotel_if_another_room_is_free(self):
        from datetime import date, timedelta

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

        check_in = date.today() + timedelta(days=10)
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
