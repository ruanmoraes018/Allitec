from django.db import models
from decimal import Decimal
from clientes.models import Cliente
from produtos.models import Produto
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from pedidos.services import finalizar_pedido

class Pedido(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.PROTECT)
    caixa = models.ForeignKey('pdvs.Caixa', on_delete=models.PROTECT, null=True, blank=True)
    cli = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    vendedor = models.ForeignKey('vendedores.Vendedor', on_delete=models.SET_NULL, null=True, blank=True)
    nome_cli = models.CharField(max_length=255, blank=True)
    fantasia_fil = models.CharField(max_length=255, blank=True)
    nome_vend = models.CharField(max_length=255, blank=True)
    tabela_preco = models.ForeignKey('tabelas_preco.TabelaPreco', on_delete=models.PROTECT, null=True, blank=True)
    situacao = models.CharField(max_length=10, choices=[('Aberto', 'Aberto'), ('Faturado', 'Faturado'), ('Cancelado', 'Cancelado')], default='Aberto')
    status_pagamento = models.CharField(max_length=15, choices=[('pendente', 'Pendente'), ('parcial', 'Parcial'), ('pago', 'Pago'),], default='pendente')
    obs = models.TextField(default="", blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dt_emi = models.DateTimeField(null=True, blank=True)
    dt_fat = models.DateTimeField(null=True, blank=True)
    motivo = models.CharField(max_length=60, blank=True, null=True)
    pagamentos = GenericRelation(
        'pedidos.Pagamento',
        related_query_name='pedido'
    )
    def __str__(self):
        return f"{self.id} - {self.cli}"
    def atualizar_total(self):
        total = sum(item.subtotal for item in self.itens.all())
        self.total = total
        return total
    def atualizar_status_pagamento(self):
        pagamentos = self.pagamentos.all()
        if not pagamentos.exists():
            self.status_pagamento = 'pendente'
            return
        total_pago = sum(p.valor for p in pagamentos if p.status == 'pago')
        if total_pago == 0:
            self.status_pagamento = 'pendente'
            novo_status = 'pendente'
        elif total_pago < self.total:
            self.status_pagamento = 'parcial'
            novo_status = 'parcial'
        else:
            self.status_pagamento = 'pago'
            novo_status = 'pago'
        return novo_status
    def processar_pagamento(self, pagamento):
        self.atualizar_status_pagamento()

        if self.situacao != "Faturado":
            finalizar_pedido(self)
        else:
            self.status_pagamento = "pago"
            self.save(update_fields=["status_pagamento"])
    def save(self, *args, **kwargs):
        self.nome_cli = self.cli.fantasia
        self.fantasia_fil = self.vinc_fil.fantasia
        self.nome_vend = self.vendedor.fantasia
        super().save(*args, **kwargs)
    @property
    def formas_convertidas(self):
        return [{"descricao": fp.forma_pgto.descricao, "valor": fp.valor} for fp in self.formas_pgto.select_related("forma_pgto").all()]
    class Meta:
        verbose_name_plural = "Pedidos"
        permissions = [
            ("clonar_pedido", "Pode clonar pedido"),
            ("faturar_pedido", "Pode faturar pedido"),
            ("cancelar_pedido", "Pode cancelar pedido"),
            ("atribuir_desconto_ped", "Pode atribuir descontos em pedido"),
            ("atribuir_acrescimo_ped", "Pode atribuir acréscimos em pedido"),
            ("vender_sem_estoque_ped", "Pode vender sem estoque"),
            ("alt_vl_ped", "Pode alterar valor de produtos em pedidos"),
            ("alterar_data_faturamento", "Pode alterar data de faturamento"),
        ]

class PedidoProduto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="produtos_vinculados_ped")
    vl_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    tp_desc_acres = models.CharField(max_length=10, choices=[('Desconto', 'Desconto'), ('Acréscimo', 'Acréscimo')], default='Desconto')
    tipo_desc = models.CharField(max_length=10, choices=[('valor', 'Valor'), ('percentual', 'Percentual')], default='valor')
    desc_acres = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    @property
    def valor_desc_real(self):
        base = (self.vl_unit or Decimal("0")) * (self.quantidade or Decimal("0"))
        if self.tipo_desc == 'percentual':
            return base * (self.desc_acres or Decimal("0")) / Decimal("100")
        else:
            return self.desc_acres or Decimal("0")
    @property
    def subtotal(self):
        base = (self.vl_unit or Decimal("0")) * (self.quantidade or Decimal("0"))
        desconto = self.valor_desc_real
        if self.tp_desc_acres == 'Desconto':
            return base - desconto
        else:
            return base + desconto
    def __str__(self):
        return f"{self.produto} ({self.quantidade})"

class PedidoFormaPgto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="formas_pgto")
    forma_pgto = models.ForeignKey("formas_pgto.FormaPgto", on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["pedido", "forma_pgto"], name="uniq_ped_formapgto")]
    def __str__(self):
        return f"{self.pedido.id} - {self.forma_pgto.descricao}"

class Pagamento(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    origem = GenericForeignKey('content_type', 'object_id')

    forma_pgto = models.ForeignKey('formas_pgto.FormaPgto', on_delete=models.PROTECT)

    gateway = models.CharField(max_length=20, null=True, blank=True)

    txid = models.CharField(max_length=100, db_index=True, null=True, blank=True)

    valor = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default='pendente')

    qr_code = models.TextField(null=True, blank=True)
    qr_base64 = models.TextField(null=True, blank=True)

    payload = models.JSONField(null=True, blank=True)

    dt_criacao = models.DateTimeField(auto_now_add=True)
    dt_pagamento = models.DateTimeField(null=True, blank=True)