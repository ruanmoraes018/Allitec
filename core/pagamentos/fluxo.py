from core.pagamentos.services import PagamentoService
from pedidos.models import Pagamento
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

def gerar_pagamentos_pedido(pedido):
    pagamentos_gerados = []
    for forma in pedido.formas_pgto.all():
        gateway = (forma.forma_pgto.gateway or "").strip().lower()
        if gateway in ["nenhum", "", "none"]:
            continue
        try:
            service = PagamentoService(forma.forma_pgto)
            result = service.gerar_pagamento(valor=forma.valor, descricao=f"Pedido {pedido.id}", email=getattr(pedido.cli, "email", None), external_reference=str(pedido.id))
            if not result:
                continue
            txid = result.get("id")
            qr_code = result.get("qr_code")
            if not txid or not qr_code:
                continue
            pagamento = Pagamento.objects.create(
                vinc_emp=pedido.vinc_emp,
                content_type=ContentType.objects.get_for_model(pedido),
                object_id=pedido.id,
                forma_pgto=forma.forma_pgto,
                valor=Decimal(str(forma.valor)),
                txid=txid,
                qr_code=qr_code,
                qr_base64=result.get("qr_base64"),
                gateway=forma.forma_pgto.gateway,
                status="pendente"
            )
            pagamentos_gerados.append({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": result.get("qr_base64"), "valor": str(pagamento.valor)})
        except Exception as e:
            continue
    return pagamentos_gerados

def gerar_pagamento_conta_receber(conta):
    formas = conta.forma_pgto

    gateway = (formas.gateway or "").strip().lower()

    if gateway in ["nenhum", "", "none"]:
        return None

    service = PagamentoService(formas)

    result = service.gerar_pagamento(
        valor=conta.saldo,
        descricao=f"Conta {conta.num_conta}",
        email=getattr(conta.cliente, "email", None),
        external_reference=str(conta.id)
    )

    if not result:
        return None

    pagamento = Pagamento.objects.create(
        content_type=ContentType.objects.get_for_model(conta),
        object_id=conta.id,
        vinc_emp=conta.vinc_emp,
        forma_pgto=formas,
        valor=conta.saldo,
        txid=result.get("id"),
        qr_code=result.get("qr_code"),
        qr_base64=result.get("qr_base64"),
        gateway=formas.gateway,
        status="pendente"
    )

    return pagamento