from django.utils import timezone
from datetime import date
from calendar import monthrange
from .models import Contrato

def contratos_do_mes():
    hoje = timezone.localdate()

    primeiro_dia = hoje.replace(day=1)
    ultimo_dia = hoje.replace(day=monthrange(hoje.year, hoje.month)[1])

    return Contrato.objects.filter(
        status='Aprovado',
        dt_exp__range=(primeiro_dia, ultimo_dia)
    ).select_related('empresa')
