from django.apps import AppConfig


class FiliaisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'filiais'

    def ready(self):
        import filiais.signals