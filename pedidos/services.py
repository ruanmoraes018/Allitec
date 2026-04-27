def finalizar_pedido(pedido, formas=None, parcelas=None, parcial=False):

    from pedidos.models import PedidoFormaPgto  # 🔥 IMPORT AQUI
    from contas_receber.models import ContaReceber  # 🔥 AQUI TAMBÉM

    from decimal import Decimal
    from django.utils import timezone

    if pedido.situacao != "Faturado":
        for item in pedido.itens.select_related('produto'):
            produto = item.produto
            produto.estoque_prod = (produto.estoque_prod or Decimal('0')) - item.quantidade
            produto.save(update_fields=["estoque_prod"])

    if formas:
        for f in formas:
            PedidoFormaPgto.objects.create(
                pedido=pedido,
                forma_pgto_id=f["forma"],
                valor=f["valor"]
            )

    if parcelas:
        for p in parcelas:
            ContaReceber.objects.create(
                vinc_emp=pedido.vinc_emp,
                vinc_fil=pedido.vinc_fil,
                cliente=pedido.cli,
                pedido=pedido,
                forma_pgto_id=p.get('forma'),
                num_conta=p.get('numero'),
                valor=Decimal(str(p.get('valor'))),
                data_vencimento=p.get('vencimento'),
                situacao='Aberta'
            )

    pedido.status_pagamento = "parcial" if parcial else "pago"
    pedido.situacao = "Faturado"
    pedido.dt_fat = timezone.now()

    pedido.save(update_fields=["status_pagamento", "situacao", "dt_fat"])