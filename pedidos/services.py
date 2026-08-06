from datetime import datetime
from formas_pgto.models import FormaPgto
from util.logs import gerar_alteracoes, registrar_log

def finalizar_pedido(pedido, formas=None, parcelas=None, parcial=False, request=None):
    from decimal import Decimal
    from django.utils import timezone
    from pedidos.models import PedidoFormaPgto
    from contas_receber.models import ContaReceber
    user = getattr(request, "user", None)
    # 🔥 verifica permissão de vender sem estoque
    pode_vender_sem_estoque = (user and user.has_perm("pedidos.vender_sem_estoque_ped"))
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
                    return {"ok": False, "erro": f"Estoque insuficiente para {produto}. Disponível: {produto.estoque_prod}!"}
                produto.estoque_prod = nova_qtd
            else:
                # 🔥 vende mesmo sem estoque (ou mantém negativo, depende da sua regra)
                produto.estoque_prod = atual - item.quantidade
            produto.save(update_fields=["estoque_prod"])
        pedido.estoque_baixado = True
    # 🔥 FORMAS DE PAGAMENTO
    if formas:
        for f in formas:
            forma = FormaPgto.objects.get(codigo=f["forma"], vinc_emp=pedido.vinc_emp)
            PedidoFormaPgto.objects.create(pedido=pedido, forma_pgto=forma, valor=f["valor"])
    # 🔥 CONTAS A RECEBER
    if parcelas:
        for p in parcelas:
            # converte data_emissao para date, caso seja string
            if isinstance(pedido.dt_fat, str):
                try: data_emissao = datetime.strptime(pedido.dt_fat, "%Y-%m-%d").date()
                except ValueError: data_emissao = datetime.today().date()
            else:
                data_emissao = pedido.dt_fat
            # converte data_vencimento
            data_vencimento = p.get('vencimento')
            if isinstance(data_vencimento, str):
                try: data_vencimento = datetime.strptime(data_vencimento, "%Y-%m-%d").date()
                except ValueError: data_vencimento = None  # ou escolha outra estratégia
            numero_preview = str(p.get("numero"))
            sufixo = numero_preview.split("/", 1)[1]
            ContaReceber.objects.create(data_emissao=p.get("data_emissao"), vinc_emp=pedido.vinc_emp, vinc_fil=pedido.vinc_fil, cliente=pedido.cli, pedido=pedido,
                forma_pgto_id=p.get("forma"), num_conta=f"P-{pedido.codigo}/{len(parcelas):02d}-{sufixo}", valor=Decimal(str(p.get("valor"))), data_vencimento=data_vencimento,
                situacao="Aberta",
            )
    # 🔥 STATUS
    pedido.status_pagamento = "parcial" if parcial else "pago"
    pedido.situacao = "Faturado"
    pedido.dt_fat = timezone.now()
    pedido.save()
    registrar_log(request=request, tipo="FATURAR", modulo="Pedido", objeto=pedido.codigo, objeto_id=pedido.id, descricao=f"Faturou o pedido nº {pedido.codigo}",
        alteracoes={
            "Valor Total": pedido.total, "Cliente": str(pedido.cli), "Vendedor": str(pedido.vendedor),"Forma de Pagamento": ", ".join(str(fp.formas_pgto) for fp in pedido.formas_pgto.all())
        }
    )