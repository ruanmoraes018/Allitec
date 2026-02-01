from django.db import models
from decimal import Decimal
from clientes.models import Cliente
from produtos.models import Produto
from tecnicos.models import Tecnico
import unicodedata
from django.utils import timezone
from django.conf import settings

class SolicitacaoPermissao(models.Model):
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitacoes_criadas"
    )
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="solicitacoes_autorizadas"
    )
    acao = models.CharField(max_length=100)  # exemplo: 'atribuir_desconto'
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

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Orcamento(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE, db_index=True)
    cli = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_index=True)
    solicitante = models.ForeignKey(Tecnico, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    fantasia_emp = models.CharField(max_length=255, blank=True)
    nome_cli = models.CharField(max_length=255, blank=True)
    nome_solicitante = models.CharField(max_length=255, blank=True)
    situacao = models.CharField(
        max_length=10,
        choices=[('Aberto', 'Aberto'), ('Faturado', 'Faturado'), ('Cancelado', 'Cancelado')],
        default='Aberto',
        db_index=True
    )
    status = models.CharField(
        max_length=15,
        choices=[('Em Produção', 'Em Produção'), ('Embalada', 'Embalada'), ('Entregue', 'Entregue'), ('Instalada', 'Instalada')],
        default='Em Produção',
        db_index=True
    )
    num_orcamento = models.CharField(max_length=25, db_index=True)
    obs_cli = models.TextField(default="", blank=True)
    pintura = models.CharField(max_length=5, choices=[
        ('Sim', 'Sim'), ('Não', 'Não')
    ], default='Sim')
    portao_social = models.CharField(max_length=5, choices=[
        ('Não', 'Não'), ('Sim', 'Sim')
    ], default='Não')
    vl_p_s = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tp_pintura = models.CharField(max_length=13, choices=[
        ('Eletrostática', 'Eletrostática'),
        ('Automotiva', 'Automotiva')
    ], default='Eletrostática')
    cor = models.CharField(
        max_length=30,
        choices=[
            ('', ''),
            ('Preto', 'Preto'), ('Branco', 'Branco'), ('Amarelo', 'Amarelo'), ('Vermelho', 'Vermelho'),
            ('Roxo Açaí', 'Roxo Açaí'), ('Azul Pepsi', 'Azul Pepsi'), ('Azul Claro', 'Azul Claro'),
            ('Cinza Claro', 'Cinza Claro'), ('Cinza Grafite', 'Cinza Grafite'), ('Verde', 'Verde'),
            ('Bege', 'Bege'), ('Bege Areia', 'Bege Areia'), ('Marrom', 'Marrom'), ('Marrom Café', 'Marrom Café'),
            ('Laranja', 'Laranja'), ('Azul Royal', 'Azul Royal'), ('Azul Marinho', 'Azul Marinho'),
            ('Verde Musgo', 'Verde Musgo'), ('Verde Bandeira', 'Verde Bandeira'), ('Vinho', 'Vinho'),
            ('Prata', 'Prata'),
        ],
        default='Preto'
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
        return f"{self.num_orcamento}"
    def atualizar_subtotal(self):
        subtotal = Decimal("0.00")
        # Portas (produtos + adicionais)
        for porta in self.portas.all():
            subtotal += sum(
                (p.subtotalP for p in porta.produtos.all()),
                Decimal("0.00")
            )
            subtotal += sum(
                (a.subtotalA for a in porta.adicionais.all()),
                Decimal("0.00")
            )
        self.subtotal = subtotal
        self.total = subtotal - (self.desconto or Decimal("0.00")) + (self.acrescimo or Decimal("0.00"))
        return self.subtotal
    def save(self, *args, **kwargs):
        self.nome_solicitante = self.solicitante.nome if self.solicitante else ''
        self.nome_cli = self.cli.fantasia if self.cli else ''
        self.fantasia_emp = self.vinc_fil.fantasia.upper() if self.vinc_fil else ''
        super().save(*args, **kwargs)
    class Meta:
        verbose_name_plural = "Orçamentos"
        permissions = [
            ("clonar_orcamento", "Pode clonar orçamento"),
            ("faturar_orcamento", "Pode faturar orçamento"),
            ("cancelar_orcamento", "Pode cancelar orçamento"),
            ("atribuir_desconto", "Pode atribuir descontos em orçamento"),
            ("atribuir_acrescimo", "Pode atribuir acréscimo em orçamento"),
        ]
# 🔥 NOVO MODELO — uma porta pertence a um orçamento
class PortaOrcamento(models.Model):
    orcamento = models.ForeignKey(
        Orcamento, on_delete=models.CASCADE, related_name="portas"
    )
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
    # Dados gerais da porta (válidos para todas)
    tp_lamina = models.CharField(max_length=25, choices=[
        ('Fechada', 'Fechada'),
        ('Transvision', 'Transvision')
    ], default='Fechada')
    tp_vao = models.CharField(max_length=50, choices=[
        ('Dentro do Vão', 'Dentro do Vão'),
        ('Fora do Vão', 'Fora do Vão'),
        ('1 Lado Dentro do Vão', '1 Lado Dentro do Vão')
    ], default='Fora do Vão')
    def __str__(self):
        return f"Porta {self.numero} do Orçamento {self.orcamento.num_orcamento}"
class PortaProduto(models.Model):
    porta = models.ForeignKey(
        PortaOrcamento, on_delete=models.CASCADE, related_name="produtos"
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="portas_produtos"
    )
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    regra_origem = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    @property
    def subtotalP(self):
        tabela = self.produto.produtotabela_set.first()
        valor = tabela.vl_prod if tabela else 0
        return valor * self.quantidade
    @property
    def totCompraP(self):
        return Decimal(str(self.produto.vl_compra)) * self.quantidade
    def __str__(self):
        return f"Porta {self.porta.numero} - {self.produto.desc_prod}"
class PortaAdicional(models.Model):
    porta = models.ForeignKey(
        PortaOrcamento, on_delete=models.CASCADE, related_name="adicionais"
    )
    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="portas_adicionais"
    )
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    @property
    def subtotalA(self):
        tabela = self.produto.produtotabela_set.first()
        valor = tabela.vl_prod if tabela else 0
        return valor * self.quantidade
    @property
    def totCompraA(self):
        return Decimal(str(self.produto.vl_compra)) * self.quantidade
    def __str__(self):
        return f"(Adicional) Porta {self.porta.numero} - {self.produto.desc_prod}"
class OrcamentoFormaPgto(models.Model):
    orcamento = models.ForeignKey("Orcamento", on_delete=models.CASCADE, related_name="formas_pgto")
    formas_pgto = models.ForeignKey("formas_pgto.FormaPgto", on_delete=models.PROTECT, related_name="usos")
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["orcamento", "formas_pgto"], name="uniq_orc_formapgto")
        ]
    def __str__(self):
        return f"{self.orcamento.id} - {self.formas_pgto.descricao}"