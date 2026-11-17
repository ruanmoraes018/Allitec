from collections import defaultdict
from decimal import Decimal, InvalidOperation
from produtos.models import Produto, CodigoProduto
from produtos.services import adicionar_estoque, retirar_estoque
from django.db import models
from pedidos.models import PedidoDevolucao, PedidoDevolucaoItem, PedidoFormaPgto, Pagamento, PedidoProduto
from formas_pgto.models import FormaPgto
from clientes.models import CreditoCliente
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from decimal import ROUND_DOWN

def buscar_produto(codigo, empresa):
    codigo = str(codigo).strip()
    cod_sec = CodigoProduto.objects.filter(codigo=codigo, vinc_emp=empresa).select_related('produto').first()
    if cod_sec:
        return cod_sec.produto
    try: return Produto.objects.get(codigo=int(codigo), vinc_emp=empresa)
    except (ValueError, Produto.DoesNotExist): raise Produto.DoesNotExist("Produto não encontrado")


def processar_estoque_caixa(itens,estoque,usuario=None,permitir_negativo=False,):
    quantidades_venda = defaultdict(Decimal)
    quantidades_devolucao = defaultdict(Decimal)
    produtos_encontrados = {}
    empresa = estoque.empresa
    # 1. Identifica os produtos utilizando o mesmo critério do PDV.
    for item in itens:
        codigo_produto = item.get('produto_id')
        if not codigo_produto:raise ValueError('Produto não informado.')
        try:produto = buscar_produto(codigo_produto, empresa)
        except Produto.DoesNotExist:
            raise ValueError(f'Produto {codigo_produto} não encontrado para esta empresa.')
        try:quantidade = Decimal(str(abs(item.get('qtd', 0))))
        except (TypeError, ValueError, InvalidOperation):raise ValueError(f'Quantidade inválida para o produto {codigo_produto}.')
        if quantidade <= 0:
            raise ValueError(f'A quantidade do produto {codigo_produto} deve ser maior que zero.')
        # Guarda pelo ID real do produto.
        produtos_encontrados[produto.pk] = produto
        if item.get('is_devolucao', False):quantidades_devolucao[produto.pk] += quantidade
        else:quantidades_venda[produto.pk] += quantidade
    # 2. Processa os produtos vendidos.
    for produto_id, quantidade in quantidades_venda.items():
        produto = produtos_encontrados[produto_id]
        retirar_estoque(estoque=estoque,produto=produto,quantidade=quantidade,usuario=usuario,descricao='Venda realizada no caixa.',permitir_negativo=permitir_negativo,)
    # 3. Processa os produtos devolvidos.
    for produto_id, quantidade in quantidades_devolucao.items():
        produto = produtos_encontrados[produto_id]
        adicionar_estoque(estoque=estoque,produto=produto,quantidade=quantidade,usuario=usuario,descricao='Devolução realizada no caixa.',)

def criar_devolucao_caixa(*,caixa,pedido,pedido_original,cliente=None,tipo,total,itens,):
    if not pedido_original:
        raise ValueError('Pedido de origem não informado para a devolução.')
    if not itens:
        raise ValueError('Nenhum item de devolução foi informado.')
    empresa = caixa.vinc_emp
    filial = caixa.vinc_fil
    usuario = caixa.usuario
    # Valida todos os itens antes de criar o cabeçalho.
    for item in itens:
        if not item.get('item_pedido_id'):
            raise ValueError('Não foi possível identificar a linha original do item de devolução.')
        try:
            quantidade = Decimal(str(item.get('quantidade', 0)))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError('Quantidade de devolução inválida.')
        if quantidade <= 0:
            raise ValueError('A quantidade devolvida deve ser maior que zero.')
    try:
        total = Decimal(str(total))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError('Valor total da devolução inválido.')
    if total <= 0:
        raise ValueError('O total da devolução deve ser maior que zero.')
    # Gera o código sequencial por empresa com proteção
    # contra concorrência.
    ultimo_codigo = (PedidoDevolucao.objects.select_for_update().filter(vinc_emp=empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0)
    devolucao = PedidoDevolucao.objects.create(codigo=ultimo_codigo + 1,vinc_emp=empresa,vinc_fil=filial,pedido=pedido_original,cliente=cliente or pedido_original.cli,usuario=usuario,
        tipo=tipo,total=total,observacao=(f'Troca efetuada no Caixa. Pedido atual: {pedido.codigo}'),
    )
    # Cria as linhas vinculadas ao pedido original.
    itens_obj = []
    for item in itens:
        itens_obj.append(PedidoDevolucaoItem(devolucao=devolucao,item_pedido_id=item['item_pedido_id'],quantidade=item['quantidade'],))
    PedidoDevolucaoItem.objects.bulk_create(itens_obj)
    return devolucao

def processar_pagamentos_caixa(*,pedido,caixa,pagamentos,):
    from lancpdvs.models import CaixaMovimento
    empresa = caixa.vinc_emp
    usuario = caixa.usuario
    total_pago = Decimal('0.00')
    movimentos = []
    pagamentos_gateway = []
    contas_prazo = []
    for pg in pagamentos:
        forma_id = pg.get('forma_id')
        if not forma_id:
            raise ValueError('Forma de pagamento não informada.')
        forma = (FormaPgto.objects.filter(codigo=forma_id,vinc_emp=empresa,).first())
        if not forma:
            raise ValueError(f'Forma de pagamento {forma_id} não encontrada.')
        try:
            valor = Decimal(str(pg.get('valor', 0)))
        except (TypeError,ValueError,InvalidOperation):
            raise ValueError(f'Valor inválido para a forma de pagamento {forma_id}.')
        if valor <= 0:
            raise ValueError('O valor do pagamento deve ser maior que zero.')
        if (forma.tipo or '').strip().upper() == 'A PRAZO':
            contas_prazo.append({'forma': forma,'valor': valor,'parcelas': max(int(pg.get('parcelas') or 1), 1),'dias': max(int(pg.get('dias') or 0), 0),})
        PedidoFormaPgto.objects.create(pedido=pedido,forma_pgto=forma,valor=valor,)
        total_pago += valor
        gateway = (getattr(forma, 'gateway', '') or '').strip().lower()
        # Pagamento só existe quando há gateway.
        if gateway and gateway not in ('nenhum', 'none'):
            content_type = ContentType.objects.get_for_model(pedido)
            pagamento = Pagamento.objects.create(vinc_emp=empresa,content_type=content_type,object_id=pedido.id,forma_pgto=forma,gateway=gateway,valor=valor,status='pendente',)
            pagamentos_gateway.append(pagamento)
        movimentos.append(CaixaMovimento(caixa=caixa,pedido=pedido,tipo='Entrada',categoria='Venda',forma_pagamento=forma,valor=valor,descricao=f'Pedido/Troca {pedido.codigo}',
            usuario=usuario,)
        )
    return {'total_pago': total_pago,'movimentos': movimentos,'pagamentos_gateway': pagamentos_gateway, 'contas_prazo': contas_prazo}

def dividir_valor(total, n):
    base = (total / n).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    return [base] * (n - 1) + [total - base * (n - 1)]

def criar_contas_receber_caixa(*, pedido, caixa, cliente, contas_prazo):
    from contas_receber.models import ContaReceber   # ajuste o import
    if not contas_prazo:
        return
    if not cliente:
        raise ValueError('Cliente é obrigatório para venda a prazo.')
    empresa = caixa.vinc_emp
    base = pedido.dt_fat.date()
    ultimo = (ContaReceber.objects.select_for_update().filter(vinc_emp=empresa)
              .aggregate(m=models.Max('codigo'))['m'] or 0)
    for c in contas_prazo:
        for i, valor in enumerate(dividir_valor(c['valor'], c['parcelas']), start=1):
            ultimo += 1
            ContaReceber.objects.create(codigo=ultimo, vinc_emp=empresa, vinc_fil=caixa.vinc_fil, cliente=cliente,pedido=pedido,num_conta=f"{pedido.codigo}/{c['parcelas']:02d}-{i}",
                valor=valor,data_emissao=base,data_vencimento=base + timedelta(days=c['dias'] * i),situacao='Aberta',
            )

def criar_credito_cliente(*,caixa,total_venda,cliente=None,pedido=None,pedido_original=None,):
    try:
        total_venda = Decimal(str(total_venda))
    except (TypeError, ValueError, InvalidOperation):
        raise ValueError('Total da venda inválido.')
    if total_venda >= 0:
        return None
    empresa = caixa.vinc_emp
    filial = caixa.vinc_fil
    usuario = caixa.usuario
    cliente_credito = (cliente or (pedido_original.cli if pedido_original else pedido.cli if pedido else None))
    if not cliente_credito:
        raise ValueError('Não foi possível criar o crédito: cliente não informado.')
    pedido_origem = pedido_original or pedido
    # Código sequencial por empresa.
    ultimo_codigo = (CreditoCliente.objects.select_for_update().filter(vinc_emp=empresa).aggregate(max_codigo=models.Max('codigo')).get('max_codigo')or 0)
    valor_credito = abs(total_venda)
    credito = CreditoCliente.objects.create(codigo=ultimo_codigo + 1,vinc_emp=empresa,vinc_fil=filial,cliente=cliente_credito,pedido_origem=pedido_origem,usuario=usuario,
        valor=valor_credito,saldo=valor_credito,situacao='Aberto',observacao=('Crédito gerado através de venda no caixa.'),
    )
    return credito

def processar_itens_caixa(*,itens,pedido,):
    itens_objs = []
    itens_devolucao = []
    total_venda = Decimal('0.00')
    total_devolucao = Decimal('0.00')
    for item in itens:
        codigo_prod = item.get('produto_id')
        if not codigo_prod:
            raise ValueError('Produto não informado.')
        try:
            produto = buscar_produto(codigo_prod,pedido.vinc_emp,)
        except Produto.DoesNotExist:
            raise ValueError(f'Produto {codigo_prod} não encontrado.')
        try:
            qtd = Decimal(str(abs(item.get('qtd', 0))))
            vl = Decimal(str(abs(item.get('preco', 0))))
        except (TypeError, ValueError, InvalidOperation):
            raise ValueError(f'Quantidade ou preço inválido para o produto {codigo_prod}.')
        if qtd <= 0:
            raise ValueError(f'A quantidade do produto {codigo_prod} deve ser maior que zero.')
        is_devolucao = item.get('is_devolucao', False)
        quantidade = -qtd if is_devolucao else qtd
        obj = PedidoProduto(pedido=pedido,produto=produto,quantidade=quantidade,vl_unit=vl,codigo_usado=codigo_prod,)
        total_venda += obj.subtotal
        itens_objs.append(obj)
        if is_devolucao:
            item_pedido_original_id = item.get('item_pedido_id')
            if not item_pedido_original_id:
                raise ValueError('Não foi possível identificar a linha original do item de devolução.')
            itens_devolucao.append({'item_pedido_id': item_pedido_original_id,'quantidade': qtd,})
            total_devolucao += qtd * vl
    PedidoProduto.objects.bulk_create(itens_objs)
    pedido.total = total_venda
    pedido.save(update_fields=['total'])
    return {'total_venda': total_venda,'total_devolucao': total_devolucao,'itens_devolucao': itens_devolucao,}