
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        HOTEL_MANAGER = 'hotel_manager', 'Hotel Manager'
        ADMIN = 'admin', "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )

    class Meta(AbstractUser.Meta):
        swappable = "AUTH_USER_MODEL"
        abstract = False
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="unique_user_email_case_insensitive",
            ),
        ]
    def __str__(self):
        return self.username
