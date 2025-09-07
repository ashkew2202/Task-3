from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator


class CustomBaseUser(AbstractUser):
    # since the default user model has a primary key with integer type,
    # we need to override it with a UUID field to make it resistant to unauthorized access
    # in the case of a stolen secret key
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    photo_url = models.TextField(
        default="", blank=True, help_text="URL of the user's profile photo"
    )


class UserProfile(models.Model):
    """
    Every Student and outsider (to be populated once the final outstie list is confirmed)
    has a UserProfile that contains their basic information and holds important state
    """

    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    name = models.CharField("Name", max_length=100, blank=False)
    email = models.EmailField("Email", unique=True)
    photo_url = models.TextField(default="", blank=True)
    auth_user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="profile"
    )
    phone_number = models.PositiveBigIntegerField(
        validators=[MaxValueValidator(9999999999), MinValueValidator(1000000000)],
        null=True,
        blank=True,
    )
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female")],
        null=True,
        blank=True,
    )
    is_outstie = models.BooleanField(
        default=False, help_text="Is the user a non-BITSian?"
    )
    reg_token = models.CharField(blank=True, null=True)
    is_disabled = models.BooleanField(default=False)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.name} - {self.email}"


class BITSianProfile(models.Model):
    static_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, max_length=36
    )
    profile = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, related_name="bits_student"
    )
    full_name = models.CharField(null=False, max_length=200)
    gender = models.CharField(
        choices=[("M", "Male"), ("F", "Female")], default="M", max_length=1
    )
    email = models.EmailField(null=False, max_length=100, unique=True)
    bits_id = models.CharField(
        null=False, max_length=20, unique=True, verbose_name="BITS ID"
    )
    room_no = models.CharField(max_length=10)
    bhavan = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "BITS Student"
        verbose_name_plural = "BITS Students"

    def __str__(self):
        return f"{self.profile.name} - {self.bits_id}"
