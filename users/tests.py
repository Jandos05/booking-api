
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserRegistrationTests(APITestCase):
    def test_register_creates_customer(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new_customer",
                "email": "customer@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username="new_customer")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertTrue(user.check_password("StrongPass123!"))



    def test_register_rejects_duplicate_email_case_insensitively(self):
        User.objects.create_user(
            username="existing_customer",
            email="customer@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "another_customer",
                "email": "CUSTOMER@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            User.objects.filter(username="another_customer").exists()
        )


    def test_register_rejects_short_password(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "short_password_user",
                "email": "short@example.com",
                "password": "123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(
            User.objects.filter(username="short_password_user").exists()
        )


    def test_register_cannot_choose_privileged_role(self):
        for role in ("admin", "hotel_manager"):
            username = f"user_{role}"
            response = self.client.post(
                reverse("register"),
                {
                    "username": username,
                    "email": f"{username}@example.com",
                    "password": "StrongPass123!",
                    "role": role,
                },
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            user = User.objects.get(username=username)
            self.assertEqual(user.role, User.Role.CUSTOMER)


class UserLoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="login_customer",
            email="login@example.com",
            password="StrongPass123!",
            role=User.Role.CUSTOMER,
        )

    def test_login_returns_jwt_tokens(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "login_customer",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "login_customer",
                "password": "WrongPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_customer",
            email="profile@example.com",
            password="StrongPass123!",
            role=User.Role.CUSTOMER,
        )

    def test_authenticated_user_can_view_own_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "profile_customer")
        self.assertEqual(response.data["role"], User.Role.CUSTOMER)

    def test_anonymous_user_cannot_view_profile(self):
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
