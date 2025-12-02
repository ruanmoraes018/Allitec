from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from orcamentos.models import Orcamento  # ajuste o caminho do modelo conforme necessário

def criar_permissoes():
    content_type = ContentType.objects.get_for_model(Orcamento)

    permissoes = [
        ('atribuir_acrescimo', 'Pode atribuir acréscimo'),
        # Adicione outras aqui se quiser
    ]

    for codename, nome in permissoes:
        perm, criada = Permission.objects.get_or_create(
            codename=codename,
            name=nome,
            content_type=content_type
        )
        print(f"{'Criada' if criada else 'Já existe'}: {codename}")

if __name__ == '__main__':
    criar_permissoes()
