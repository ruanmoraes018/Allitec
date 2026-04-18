from core.pagamentos.services import PagamentoService
from pedidos.models import Pagamento

def gerar_pagamentos_pedido(pedido):
    pagamentos_gerados = []

    for forma in pedido.formas_pgto.all():

        if forma.forma_pgto.gateway == "nenhum":
            continue

        service = PagamentoService(forma.forma_pgto)

        result = service.gerar_pagamento(
            valor=forma.valor,
            descricao=f"Pedido {pedido.id}",
            email=pedido.cli.email or "teste@email.com"
        )

        pagamento = Pagamento.objects.create(
            pedido=pedido,
            forma_pgto=forma.forma_pgto,
            valor=forma.valor,
            txid=result["id"],
            qr_code=result["qr_code"],
            gateway=forma.forma_pgto.gateway,
            status="pendente"
        )

        pagamentos_gerados.append({
            "txid": pagamento.txid,
            "qr_code": pagamento.qr_code,
            "qr_base64": result.get("qr_base64"),
            "valor": str(pagamento.valor)
        })

    return pagamentos_gerados