from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmpresaCaseInsensitiveBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, empresa_id=None, **kwargs):
        UserModel = get_user_model()
        if username is None or password is None:
            return None

        # Filtra pelo usuário ignorando maiúsculas/minúsculas + empresa
        query = {"username__iexact": username}
        if empresa_id:
            query["empresa_id"] = empresa_id

        try:
            user = UserModel.objects.get(**query)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
