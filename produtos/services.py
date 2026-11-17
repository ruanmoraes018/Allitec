from .models import Alerta, SaldoEstoque, MovimentoEstoque
from django.urls import reverse
from decimal import Decimal
from django.db import transaction
from estoques.models import Estoque

def criar_alerta(*, empresa, tipo, referencia, titulo, descricao, usuarios=None, remetente=None, verb=None, dados=None,):
    alerta = Alerta.objects.filter(empresa=empresa, tipo=tipo, referencia=referencia, status='Aberto').first()
    if alerta:
        return alerta, False
    url_destino = None
    try:
        if tipo == 'ESTOQUE_MINIMO' or tipo == 'ESTOQUE_MAXIMO':
            # Aponta para a view de atualização do produto usando o código como referência
            url_destino = reverse('att-produto', kwargs={'codigo': referencia})
        # elif tipo == 'CONTA_RECEBER':
        #     # Exemplo de link para contas a receber
        #     url_destino = reverse('detalhar_conta_receber', kwargs={'pk': referencia})
        # Adicione outros tipos aqui conforme seu sistema crescer...
    except Exception as e:
        raise e
    alerta = Alerta.objects.create(empresa=empresa, tipo=tipo, referencia=referencia, titulo=titulo, descricao=descricao, status='Aberto', url=url_destino)
    return alerta, True

def resolver_alerta(*, empresa, tipo, referencia):
    # Resolve um alerta aberto.
    alerta = Alerta.objects.filter(empresa=empresa, tipo=tipo, referencia=referencia, status='Aberto').first()
    if not alerta:
        return None
    alerta.status = 'Resolvido'
    alerta.save(update_fields=['status'])
    return alerta

def obter_saldo(estoque, produto, bloquear=False):
    qs = SaldoEstoque.objects
    if bloquear:
        qs = qs.select_for_update()
    saldo, _ = qs.get_or_create(estoque=estoque, produto=produto, defaults={'quantidade': Decimal('0.000'), 'estoque_minimo': Decimal('0.000'), 'estoque_maximo': Decimal('0.000'),})
    return saldo

@transaction.atomic
def adicionar_estoque(estoque, produto, quantidade, usuario=None, descricao=None):
    quantidade = Decimal(str(quantidade))
    if quantidade <= 0:
        raise ValueError('A quantidade deve ser maior que zero.')
    saldo = obter_saldo(estoque, produto, bloquear=True)
    saldo_anterior = saldo.quantidade
    saldo.quantidade += quantidade
    saldo.save(update_fields=['quantidade', 'data_atualizacao'])
    movimento = MovimentoEstoque.objects.create(estoque=estoque,produto=produto,quantidade=quantidade,tipo=MovimentoEstoque.ENTRADA,saldo_anterior=saldo_anterior,
        saldo_posterior=saldo.quantidade,descricao=descricao,usuario=usuario,
    )
    return movimento

@transaction.atomic
def retirar_estoque(estoque,produto,quantidade,usuario=None,descricao=None,permitir_negativo=False):
    quantidade = Decimal(str(quantidade))
    if quantidade <= 0:
        raise ValueError('A quantidade deve ser maior que zero.')
    saldo = obter_saldo(estoque, produto, bloquear=True)
    saldo_anterior = saldo.quantidade
    if (not permitir_negativo and saldo.quantidade < quantidade):
        raise ValueError(f'Estoque insuficiente. Saldo atual: {saldo.quantidade}. Solicitado: {quantidade}.')
    saldo.quantidade -= quantidade
    saldo.save(update_fields=['quantidade', 'data_atualizacao'])
    movimento = MovimentoEstoque.objects.create(estoque=estoque,produto=produto,quantidade=quantidade,tipo=MovimentoEstoque.SAIDA,saldo_anterior=saldo_anterior,
        saldo_posterior=saldo.quantidade,descricao=descricao,usuario=usuario,
    )
    return movimento

@transaction.atomic
def ajustar_estoque(estoque, produto, nova_quantidade, usuario=None, descricao=None):
    nova_quantidade = Decimal(str(nova_quantidade))
    if nova_quantidade < 0:
        raise ValueError('A quantidade não pode ser negativa.')
    saldo = obter_saldo(estoque, produto, bloquear=True)
    saldo_anterior = saldo.quantidade
    # Quanto o estoque mudou
    diferenca = nova_quantidade - saldo_anterior
    # Não há alteração
    if diferenca == 0:
        return None
    saldo.quantidade = nova_quantidade
    saldo.save(update_fields=['quantidade', 'data_atualizacao'])
    movimento = MovimentoEstoque.objects.create(estoque=estoque,produto=produto,quantidade=abs(diferenca),tipo=MovimentoEstoque.AJUSTE,saldo_anterior=saldo_anterior,
        saldo_posterior=nova_quantidade,descricao=descricao,usuario=usuario,
    )
    return movimento

@transaction.atomic
def transferir_estoque(estoque_origem, estoque_destino, produto, quantidade, usuario=None, descricao=None):
    quantidade = Decimal(str(quantidade))
    if quantidade <= 0:
        raise ValueError('A quantidade deve ser maior que zero.')
    if estoque_origem.pk == estoque_destino.pk:
        raise ValueError('O estoque de origem e destino devem ser diferentes.')
    # Bloqueia os dois saldos sempre na mesma ordem. Isso evita deadlocks em transferências simultâneas.
    estoques = sorted([estoque_origem, estoque_destino], key=lambda estoque: estoque.pk)
    saldos = {}
    for estoque in estoques:
        saldos[estoque.pk] = obter_saldo(estoque, produto, bloquear=True)
    saldo_origem = saldos[estoque_origem.pk]
    saldo_destino = saldos[estoque_destino.pk]
    # Verifica saldo disponível na origem
    if saldo_origem.quantidade < quantidade:
        raise ValueError(f'Estoque insuficiente no estoque de origem. Saldo atual: {saldo_origem.quantidade}. Solicitado: {quantidade}.' )
    # Guarda os saldos anteriores
    saldo_origem_anterior = saldo_origem.quantidade
    saldo_destino_anterior = saldo_destino.quantidade
    # Atualiza os saldos
    saldo_origem.quantidade -= quantidade
    saldo_destino.quantidade += quantidade
    saldo_origem.save(update_fields=['quantidade', 'data_atualizacao'])
    saldo_destino.save(update_fields=['quantidade', 'data_atualizacao'])
    # Movimento de saída da origem
    movimento_saida = MovimentoEstoque.objects.create(estoque=estoque_origem, produto=produto, quantidade=quantidade, tipo=MovimentoEstoque.TRANSFERENCIA,
        saldo_anterior=saldo_origem_anterior,saldo_posterior=saldo_origem.quantidade,descricao=(descricao or f'Transferência para {estoque_destino}'),usuario=usuario,
    )
    # Movimento de entrada no destino
    movimento_entrada = MovimentoEstoque.objects.create(estoque=estoque_destino, produto=produto, quantidade=quantidade, tipo=MovimentoEstoque.TRANSFERENCIA,
        saldo_anterior=saldo_destino_anterior,saldo_posterior=saldo_destino.quantidade,descricao=(descricao or f'Transferência de {estoque_origem}'),usuario=usuario,
    )
    return movimento_saida, movimento_entrada

@transaction.atomic
def efetivar_item_entrada(item, usuario=None):
    """
    Adiciona o item da Entrada ao estoque escolhido no item
    e atualiza o último preço de compra do produto.
    """

    entrada = item.entrada
    produto = item.produto
    estoque = item.estoque

    if not estoque:
        raise ValueError(
            f'O produto {produto} não possui estoque definido '
            f'na entrada {entrada.numeracao}.'
        )

    # Garante que o estoque pertence à filial da entrada.
    if estoque.filial_id != entrada.vinc_fil_id:
        raise ValueError(
            f'O estoque selecionado para o produto {produto} '
            f'não pertence à filial da entrada.'
        )

    movimento = adicionar_estoque(
        estoque=estoque,
        produto=produto,
        quantidade=item.quantidade,
        usuario=usuario,
        descricao=(
            f'Entrada {entrada.tipo}: {entrada.numeracao}'
        )
    )

    # Guarda o preço de compra anterior, caso esse campo exista
    # no modelo Entrada.
    entrada.pr_compra_ant = produto.vl_compra

    # Atualiza o último preço de compra.
    produto.vl_compra = item.preco_unitario

    produto.save(
        update_fields=['vl_compra']
    )

    return movimento

def cancelar_item_entrada(item, usuario=None):
    """
    Retira do estoque a quantidade adicionada pela entrada.

    Utiliza o mesmo estoque registrado no EntradaProduto.
    Não permite que o saldo fique negativo.
    """

    entrada = item.entrada
    produto = item.produto
    estoque = item.estoque

    if not estoque:
        raise ValueError(
            f'O produto {produto} não possui estoque definido '
            f'na entrada {entrada.numeracao}.'
        )

    if estoque.filial_id != entrada.vinc_fil_id:
        raise ValueError(
            f'O estoque selecionado para o produto {produto} '
            f'não pertence à filial da entrada.'
        )

    movimento = retirar_estoque(
        estoque=estoque,
        produto=produto,
        quantidade=item.quantidade,
        usuario=usuario,
        descricao=(
            f'Cancelamento da entrada '
            f'{entrada.tipo}: {entrada.numeracao}'
        ),
        permitir_negativo=False,
    )

    return movimento