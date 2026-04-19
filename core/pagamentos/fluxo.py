from core.pagamentos.services import PagamentoService
from pedidos.models import Pagamento
from decimal import Decimal

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
            pagamento = Pagamento.objects.create(pedido=pedido, forma_pgto=forma.forma_pgto, valor=Decimal(str(forma.valor)), txid=txid, qr_code=qr_code, qr_base64=result.get("qr_base64"), gateway=forma.forma_pgto.gateway, status="pendente" )
            pagamentos_gerados.append({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": result.get("qr_base64"), "valor": str(pagamento.valor)})
        except Exception as e:
            continue
    return pagamentos_gerados