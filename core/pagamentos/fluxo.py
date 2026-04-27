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

def gerar_pagamento_conta_receber(conta, forma, valor):
    gateway = (forma.gateway or "").strip().lower()
    if gateway in ["", "nenhum", "none"]:
        return None
    service = PagamentoService(forma)
    result = service.gerar_pagamento(
        valor=valor,
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
        forma_pgto=forma,
        valor=valor,
        txid=result.get("id"),
        qr_code=result.get("qr_code"),
        qr_base64=result.get("qr_base64"),
        gateway=forma.gateway,
        status="pendente"
    )
    return pagamento

def gerar_pagamentos_orcamento(orcamento):
    pagamentos_gerados = []
    for forma in orcamento.formas_pgto.all():
        gateway = (forma.formas_pgto.gateway or "").strip().lower()
        if gateway in ["", "nenhum", "none"]:
            continue
        try:
            service = PagamentoService(forma.formas_pgto)
            result = service.gerar_pagamento(
                valor=forma.valor,
                descricao=f"Orçamento {orcamento.id}",
                email=getattr(orcamento.cli, "email", None),
                external_reference=str(orcamento.id)
            )
            if not result:
                continue
            txid = result.get("id")
            qr_code = result.get("qr_code")
            if not txid or not qr_code:
                continue
            pagamento = Pagamento.objects.create(
                vinc_emp=orcamento.vinc_emp,
                content_type=ContentType.objects.get_for_model(orcamento),
                object_id=orcamento.id,
                forma_pgto=forma.formas_pgto,
                valor=Decimal(str(forma.valor)),
                txid=txid,
                qr_code=qr_code,
                qr_base64=result.get("qr_base64"),
                gateway=forma.formas_pgto.gateway,
                status="pendente"
            )
            pagamentos_gerados.append({
                "txid": pagamento.txid,
                "qr_code": pagamento.qr_code,
                "qr_base64": pagamento.qr_base64,
                "valor": str(pagamento.valor)
            })
        except Exception:
            continue
    return pagamentos_gerados