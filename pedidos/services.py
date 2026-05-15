def finalizar_pedido(pedido, formas=None, parcelas=None, parcial=False, request=None):
    from decimal import Decimal
    from django.utils import timezone

    from pedidos.models import PedidoFormaPgto
    from contas_receber.models import ContaReceber

    user = getattr(request, "user", None)

    # 🔥 verifica permissão de vender sem estoque
    pode_vender_sem_estoque = (
        user and user.has_perm("pedidos.vender_sem_estoque_ped")
    )

    # 🔥 BAIXA DE ESTOQUE
    if not getattr(pedido, "estoque_baixado", False):

        for item in pedido.itens.select_related('produto'):
            produto = item.produto

            atual = produto.estoque_prod or Decimal('0')

            # 🔥 regra principal
            if not pode_vender_sem_estoque:
                nova_qtd = atual - item.quantidade

                # bloqueia venda sem estoque
                if nova_qtd < 0:
                    return {
                        "ok": False,
                        "erro": f"Estoque insuficiente para {produto}. Disponível: {produto.estoque_prod}!"
                    }

                produto.estoque_prod = nova_qtd
            else:
                # 🔥 vende mesmo sem estoque (ou mantém negativo, depende da sua regra)
                produto.estoque_prod = atual - item.quantidade

            produto.save(update_fields=["estoque_prod"])

        pedido.estoque_baixado = True

    # 🔥 FORMAS DE PAGAMENTO
    if formas:
        for f in formas:
            PedidoFormaPgto.objects.create(
                pedido=pedido,
                forma_pgto_id=f["forma"],
                valor=f["valor"]
            )

    # 🔥 CONTAS A RECEBER
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

    # 🔥 STATUS
    pedido.status_pagamento = "parcial" if parcial else "pago"
    pedido.situacao = "Faturado"
    pedido.dt_fat = timezone.now()

    pedido.save()