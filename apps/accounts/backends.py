from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Allows authentication with email, username prefix (e.g. 'kuxhagr' for 'kuxhagr@quickbite.com'),
    or exact match.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')
        if not username:
            return None

        username = username.strip()

        # Try exact email match first
        user = User.objects.filter(email__iexact=username).first()

        # Try first_name match (e.g. 'kuxhagr', 'Kushagr', 'rahul')
        if not user:
            user = User.objects.filter(first_name__iexact=username).first()

        # If not found, try username prefix (e.g. kuxhagr -> kuxhagr@...)
        if not user:
            user = User.objects.filter(
                Q(email__istartswith=f"{username}@") |
                Q(email__iexact=f"{username}@quickbite.com")
            ).first()

        # If not found, try phone
        if not user and username.replace('+', '').isdigit():
            user = User.objects.filter(phone=username).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

