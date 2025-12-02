from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password
from .models import Usuario
from empresas.models import Empresa
from django.db import transaction

@receiver(post_save, sender=Empresa)
def criar_usuario_padrao(sender, instance, created, **kwargs):
    """
    Cria um usuário padrão 'allitec' vinculado à empresa quando gerar_filial=True.
    """
    if created and instance.gerar_filial:
        # Usar transação para garantir consistência
        with transaction.atomic():
            # Verifica se já existe o usuário para essa empresa
            if not Usuario.objects.filter(username="allitec", empresa=instance).exists():
                Usuario.objects.create(
                    username="allitec",
                    empresa=instance,
                    password=make_password("@admin@"),
                    first_name="ALLITEC"
                    # filial pode ser None ou definida se você criar a filial principal aqui
                )


