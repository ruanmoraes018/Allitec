from django.db import models
from decimal import Decimal, InvalidOperation
from clientes.models import Cliente
from produtos.models import Produto
from tecnicos.models import Tecnico
import unicodedata
from django.utils import timezone
from django.conf import settings

class SolicitacaoPermissao(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='solicitacoes_permissao')
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="solicitacoes_criadas"
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_autorizadas"
    )
    acao = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=[
            ('Pendente', 'Pendente'),
            ('Aprovada', 'Aprovada'),
            ('Negada', 'Negada'),
            ('Expirada', 'Expirada')
        ],
        default='Pendente'
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()

    def esta_ativa(self):
        return self.status == 'Pendente' and timezone.now() < self.expira_em

    def save(self, *args, **kwargs):
        if not self.vinc_emp_id:
            if self.solicitante and getattr(self.solicitante, 'empresa', None):
                self.vinc_emp = self.solicitante.empresa
        super().save(*args, **kwargs)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Orcamento(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.PROTECT, null=True, db_index=True)
    tabela_preco = models.ForeignKey('tabelas_preco.TabelaPreco', on_delete=models.PROTECT, null=True, blank=True)
    cli = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, db_index=True)
    solicitante = models.ForeignKey(Tecnico, on_delete=models.PROTECT, null=True, blank=True, db_index=True)
    fornecedor = models.ForeignKey('fornecedores.Fornecedor', on_delete=models.SET_NULL, null=True, blank=True, db_index=True)
    fantasia_emp = models.CharField(max_length=255, blank=True)
    nome_cli = models.CharField(max_length=255, blank=True)
    nome_solicitante = models.CharField(max_length=255, blank=True)
    nome_fornecedor = models.CharField(max_length=255, blank=True)
    situacao = models.CharField(max_length=10, choices=[('Aberto', 'Aberto'), ('Faturado', 'Faturado'), ('Cancelado', 'Cancelado')], default='Aberto', db_index=True)
    status = models.CharField(max_length=15, choices=[('Em Produção', 'Em Produção'), ('Embalada', 'Embalada'), ('Entregue', 'Entregue'), ('Instalada', 'Instalada')], default='Em Produção', db_index=True)
    status_pagamento = models.CharField(
        max_length=15,
        choices=[
            ('Pendente', 'Pendente'),
            ('Parcial', 'Parcial'),
            ('Pago', 'Pago'),
        ],
        default='Pendente',
        db_index=True
    )
    num_orcamento = models.CharField(max_length=25, db_index=True)
    obs_cli = models.TextField(default="", blank=True)
    pintura = models.CharField(max_length=5, choices=[('Sim', 'Sim'), ('Não', 'Não')], default='Sim')
    portao_social = models.CharField(max_length=5, choices=[('Não', 'Não'), ('Sim', 'Sim')], default='Não')
    vl_p_s = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    tp_pintura = models.CharField(max_length=13, choices=[('Eletrostática', 'Eletrostática'), ('Automotiva', 'Automotiva')], default='Eletrostática')
    cor = models.CharField(max_length=30,
        choices=[
            ('', ''), ('Preto', 'Preto'), ('Branco', 'Branco'), ('Amarelo', 'Amarelo'), ('Vermelho', 'Vermelho'), ('Roxo Açaí', 'Roxo Açaí'), ('Azul Pepsi', 'Azul Pepsi'), ('Azul Claro', 'Azul Claro'),
            ('Cinza Claro', 'Cinza Claro'), ('Cinza Grafite', 'Cinza Grafite'), ('Cinza Chumbo', 'Cinza Chumbo'), ('Chumbo', 'Chumbo'), ('Verde', 'Verde'), ('Bege', 'Bege'), ('Bege Areia', 'Bege Areia'), ('Marrom', 'Marrom'), ('Marrom Café', 'Marrom Café'),
            ('Laranja', 'Laranja'), ('Azul Royal', 'Azul Royal'), ('Azul Marinho', 'Azul Marinho'), ('Azul Pepsi', 'Azul Pepsi'), ('Verde Musgo', 'Verde Musgo'), ('Verde Bandeira', 'Verde Bandeira'), ('Vinho', 'Vinho'), ('Prata', 'Prata'),
        ], default='Preto'
    )
    obs_form_pgto = models.TextField(default="", blank=True)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    acrescimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dt_emi = models.DateTimeField(null=True, blank=True, db_index=True)
    dt_fat = models.DateTimeField(null=True, blank=True, db_index=True)
    dt_ent = models.DateTimeField(null=True, blank=True, db_index=True)
    motivo = models.CharField(max_length=60, blank=True, null=True)

    def __str__(self):
        return f"Orçamento - {self.id}"
    def atualizar_status_pagamento(self):
        from pedidos.models import Pagamento
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(self)

        pagamentos = Pagamento.objects.filter(
            content_type=ct,
            object_id=self.id
        )

        if not pagamentos.exists():
            self.status_pagamento = 'Pendente'
        elif all(p.status == 'approved' for p in pagamentos):
            self.status_pagamento = 'Pago'
        elif any(p.status == 'approved' for p in pagamentos):
            self.status_pagamento = 'Parcial'
        else:
            self.status_pagamento = 'Pendente'

        self.save(update_fields=['status_pagamento'])
    def atualizar_subtotal(self):
        subtotal = Decimal("0.00")
        for porta in self.portas.all():
            subtotal += sum((p.subtotalP for p in porta.produtos.all()), Decimal("0.00"))
            subtotal += sum((a.subtotalA for a in porta.adicionais.all()), Decimal("0.00"))
        self.subtotal = subtotal
        self.total = subtotal - (self.desconto or Decimal("0.00")) + (self.acrescimo or Decimal("0.00"))
        return self.subtotal

    def save(self, *args, **kwargs):
        self.nome_solicitante = getattr(self.solicitante, 'nome', '')
        self.nome_cli = getattr(self.cli, 'fantasia', '')
        self.nome_fornecedor = getattr(self.fornecedor, 'fantasia', '')
        self.fantasia_emp = getattr(self.vinc_fil, 'fantasia', '').upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Orçamentos"
        permissions = [
            ("clonar_orcamento", "Pode clonar orçamento"), ("faturar_orcamento", "Pode faturar orçamento"), ("cancelar_orcamento", "Pode cancelar orçamento"),
            ("atribuir_desconto", "Pode atribuir descontos em orçamento"), ("atribuir_acrescimo", "Pode atribuir acréscimo em orçamento"),
            ("alterar_dt_venc_orc", "Pode alterar a data de vencimento na fatura de orçamento"), ("alterar_dt_fat_orc", "Pode alterar a data de faturamento na fatura de orçamento"),
        ]
# 🔥 NOVO MODELO — uma porta pertence a um orçamento
class PortaOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name="portas")
    numero = models.PositiveIntegerField(default=1)  # Porta 1, Porta 2…
    largura = models.DecimalField(max_digits=10, decimal_places=2)
    altura = models.DecimalField(max_digits=10, decimal_places=2)
    qtd_lam = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    m2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    larg_corte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    alt_corte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rolo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    peso = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    fator_peso = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    eixo_motor = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    tp_lamina = models.CharField(max_length=25, choices=[('Fechada', 'Fechada'), ('Transvision', 'Transvision')], default='Fechada')
    tp_vao = models.CharField(max_length=50, choices=[('Dentro do Vão', 'Dentro do Vão'), ('Fora do Vão', 'Fora do Vão'), ('1 Lado Dentro do Vão', '1 Lado Dentro do Vão')], default='Fora do Vão')
    op_guia_e = models.CharField(verbose_name="Opção Guia Esquerdo", max_length=13, choices=[('Dentro do Vão', 'Dentro do Vão'), ('Fora do Vão', 'Fora do Vão')], default='Dentro do Vão')
    op_guia_d = models.CharField(verbose_name="Opção Guia Direito", max_length=13, choices=[('Dentro do Vão', 'Dentro do Vão'), ('Fora do Vão', 'Fora do Vão')], default='Dentro do Vão')
    def __str__(self):
        return f"Porta {self.numero} do Orçamento {self.orcamento.id}"

class PortaProduto(models.Model):
    porta = models.ForeignKey(PortaOrcamento, on_delete=models.CASCADE, related_name="produtos")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="portas_produtos")
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    regra_origem = models.CharField(max_length=50, null=True, blank=True)

    @property
    def subtotalP(self):
        return self.valor_total or Decimal("0.00")

    @property
    def totCompraP(self):
        try:
            vl = self.produto.vl_compra
            if vl in (None, ""):
                return Decimal("0.00")

            vl = str(vl).replace(",", ".").strip()
            return Decimal(vl) * (self.quantidade or Decimal("0"))
        except InvalidOperation:
            return Decimal("0.00")

    def __str__(self):
        return f"Porta {self.porta.numero} - {self.produto.desc_prod}"

class PortaAdicional(models.Model):
    porta = models.ForeignKey(PortaOrcamento, on_delete=models.CASCADE, related_name="adicionais")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="portas_adicionais")
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    regra_origem = models.CharField(max_length=50, null=True, blank=True)
    LADO_CHOICES = (
        ('', '---------'),
        ('E', 'Esquerdo'),
        ('D', 'Direito'),
        ('C', 'Centro'),
    )
    lado = models.CharField(max_length=1, choices=LADO_CHOICES, blank=True, default='')

    @property
    def subtotalA(self):
        return self.valor_total or Decimal("0.00")

    @property
    def totCompraA(self):
        try:
            vl = self.produto.vl_compra
            if vl in (None, ""):
                return Decimal("0.00")
            vl = str(vl).replace(",", ".").strip()
            return Decimal(vl) * (self.quantidade or Decimal("0"))
        except InvalidOperation:
            return Decimal("0.00")

    def __str__(self):
        return f"(Adicional) Porta {self.porta.numero} - {self.produto.desc_prod}"

class OrcamentoFormaPgto(models.Model):
    orcamento = models.ForeignKey("Orcamento", on_delete=models.CASCADE, related_name="formas_pgto")
    formas_pgto = models.ForeignKey("formas_pgto.FormaPgto", on_delete=models.PROTECT, related_name="usos")
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    parcelas = models.PositiveIntegerField(default=1)
    dias_intervalo = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["orcamento", "formas_pgto"], name="uniq_orc_formapgto")]

    def __str__(self):
        return f"{self.orcamento.id} - {self.formas_pgto.descricao}"