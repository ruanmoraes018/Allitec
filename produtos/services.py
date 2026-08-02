from notifications.signals import notify
from .models import Alerta
from django.urls import reverse

def criar_alerta(
    *,
    empresa,
    tipo,
    referencia,
    titulo,
    descricao,
    usuarios=None,
    remetente=None,
    verb=None,
    dados=None,
):

    alerta = Alerta.objects.filter(
        empresa=empresa,
        tipo=tipo,
        referencia=referencia,
        status='Aberto'
    ).first()

    if alerta:
        return alerta, False

    url_destino = None
    try:
        if tipo == 'ESTOQUE_MINIMO' or tipo == 'ESTOQUE_MAXIMO':
            # Aponta para a view de atualização do produto usando o código como referência
            url_destino = reverse('att-produto', kwargs={'codigo': referencia})
        # elif tipo == 'CONTA_RECEBER':
        #     # Exemplo de link para contas a receber
        #     url_destino = reverse('detalhar_conta_receber', kwargs={'pk': referencia})
        # Adicione outros tipos aqui conforme seu sistema crescer...
    except Exception as e:
        raise e

    alerta = Alerta.objects.create(
        empresa=empresa,
        tipo=tipo,
        referencia=referencia,
        titulo=titulo,
        descricao=descricao,
        status='Aberto',
        url=url_destino
    )

    return alerta, True

def resolver_alerta(*, empresa, tipo, referencia):
    # Resolve um alerta aberto.

    alerta = Alerta.objects.filter(empresa=empresa, tipo=tipo, referencia=referencia, status='Aberto').first()

    if not alerta:
        return None

    alerta.status = 'Resolvido'
    alerta.save(update_fields=['status'])
    return alerta