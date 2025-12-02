# usuarios/auth_backends.py
from django.contrib.auth.backends import ModelBackend
from .models import Usuario

class FilialBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, empresa_id=None, **kwargs):
        if username is None or password is None or empresa_id is None:
            return None

        try:
            user = Usuario.objects.get(
                username__iexact=username.strip().lower(),
                empresa_id=empresa_id
            )
        except Usuario.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None