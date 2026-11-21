import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from apps.core.models import BaseModel

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
        ('delivery_partner', 'Delivery Partner'),
        ('kitchen_staff', 'Kitchen Staff'),
    )

    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True, db_index=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer', db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # Delivery partner fields
    is_online = models.BooleanField(default=False, db_index=True)
    current_lat = models.FloatField(null=True, blank=True)
    current_lng = models.FloatField(null=True, blank=True)
    last_location_updated_at = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        name = self.get_full_name() or self.email
        return f"{name} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def username(self):
        """Compatibility property for templates and tools expecting user.username."""
        if self.first_name:
            return self.first_name
        return self.email.split('@')[0] if '@' in self.email else self.email

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_kitchen(self):
        return self.role == 'kitchen_staff'

    @property
    def is_delivery(self):
        return self.role == 'delivery_partner'


class Address(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=50, default='Home') # Home, Work, Other
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, default='New Delhi')
    pincode = models.CharField(max_length=10)
    latitude = models.FloatField(default=28.6139) # Default New Delhi
    longitude = models.FloatField(default=77.2090)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f"{self.title}: {self.address_line1}, {self.city}"

    def save(self, *args, **kwargs):
        if self.is_default:
            # Unset default on user's other addresses
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

