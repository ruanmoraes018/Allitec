from filiais.models import LogUsuario
from decimal import Decimal
from datetime import date, datetime


def converter_valor(valor):
    if valor is None:
        return None

    if isinstance(valor, Decimal):
        return float(valor)

    if isinstance(valor, (date, datetime)):
        return valor.isoformat()

    return str(valor)


def gerar_alteracoes(obj_antigo=None, obj_novo=None):
    alteracoes = {}

    modelo = obj_novo or obj_antigo

    for field in modelo._meta.fields:

        if field.name == "id":
            continue

        if field.name == "id":
            continue

        antes = getattr(obj_antigo, field.name) if obj_antigo else None
        depois = getattr(obj_novo, field.name) if obj_novo else None

        if antes != depois:
            alteracoes[str(field.verbose_name)] = {
                "antes": converter_valor(antes),
                "depois": converter_valor(depois)
            }

    return alteracoes

def registrar_log(request, tipo, modulo, objeto, descricao, objeto_id=None, alteracoes=None):
    LogUsuario.objects.create(
        usuario=request.user, empresa=request.user.empresa, filial=request.user.filial_user, tipo=tipo, modulo=modulo, objeto=objeto, objeto_id=objeto_id, descricao=descricao,
        alteracoes=alteracoes
    )