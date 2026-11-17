from django.db import models
from datetime import datetime
import unicodedata
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.db import transaction
from decimal import Decimal

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

class Cliente(models.Model):
    # ── Identificação ────────────────────────────────────────────────────────
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey("filiais.Filial", on_delete=models.SET_NULL, null=True)
    situacao = models.CharField(max_length=10, verbose_name="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')])
    pessoa = models.CharField(max_length=10, verbose_name="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')])
    avulso = models.BooleanField(default=False, verbose_name="Cliente Avulso")
    # ── Documentos ───────────────────────────────────────────────────────────
    cpf_cnpj = models.CharField(max_length=25)
    ie = models.CharField(max_length=20,  blank=True, null=True)
    ie_st = models.CharField(max_length=20,  blank=True, null=True, verbose_name="IE ST", default="")
    im = models.CharField(max_length=20,  blank=True, null=True, verbose_name="Inscrição Municipal", default="")
    suframa = models.CharField(max_length=20,  blank=True, null=True, default="")
    cnae = models.CharField(max_length=10,  blank=True, null=True, verbose_name="CNAE", default="")
    ind_ie = models.CharField(max_length=10,  verbose_name="Indicador IE", choices=[('1', 'Contribuinte'), ('2', 'Isento'), ('9', 'Não contribuinte')], default="")
    regime_tributario = models.CharField(max_length=20, blank=True, null=True,
        verbose_name="Regime Tributário", choices=[('1', 'Simples Nacional'), ('2', 'Simples Nacional – Excesso de Sublimite'), ('3', 'Regime Normal')
    ], default="")
    # ── Razão / Fantasia ─────────────────────────────────────────────────────
    razao_social = models.CharField(max_length=150)
    fantasia = models.CharField(max_length=150)
    # ── Endereço ─────────────────────────────────────────────────────────────
    cep = models.CharField(max_length=10)
    endereco = models.CharField(max_length=100)
    numero = models.CharField(max_length=10)
    complem = models.CharField(max_length=30, blank=True, default="")
    bairro = models.ForeignKey(Bairro, on_delete=models.SET_NULL, null=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey(Estado,  on_delete=models.SET_NULL, null=True)
    # ── Contato ──────────────────────────────────────────────────────────────
    tel = models.CharField(max_length=30, blank=True, default="")
    tel2 = models.CharField(max_length=30, blank=True, default="", verbose_name="Telefone 2 / WhatsApp")
    email = models.EmailField(max_length=100, blank=True, default="")
    # ── Dados comerciais ─────────────────────────────────────────────────────
    somente_avista = models.BooleanField(default=False, verbose_name="Vender apenas à vista")
    limite_credito = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Limite de Crédito")
    bloqueado = models.BooleanField(default=False, verbose_name="Bloqueado para Vendas")
    motivo_bloqueio = models.CharField(max_length=200, blank=True, default="")
    desconto_padrao = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="Desconto Padrão (%)")
    # ── Datas e observações ──────────────────────────────────────────────────
    dt_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    dt_fundacao = models.DateField(null=True, blank=True, verbose_name="Data de Fundação")
    dt_reg = models.DateField(null=True, blank=True, verbose_name="Data de Registro", db_index=True)
    dt_ult_compra = models.DateField(null=True, blank=True, verbose_name="Última Compra")
    observacoes = models.TextField(blank=True, default="")
    # ── Limite disponível ────────────────────────────────────────────────────
    @property
    def saldo_devedor(self) -> Decimal:
        resultado = self.contas_receber_orc.filter(situacao='Aberta').aggregate(total=models.Sum('valor'))['total']
        return resultado or Decimal("0.00")

    @property
    def limite_disponivel(self) -> Decimal:
        if self.bloqueado or self.somente_avista or self.limite_credito <= 0:
            return Decimal("0.00")
        disponivel = self.limite_credito - self.saldo_devedor
        return max(disponivel, Decimal("0.00"))

    def pode_comprar_a_prazo(self, valor_venda: Decimal) -> tuple[bool, str]:
        if self.situacao == 'Inativo':
            return False, "Cliente inativo."
        if self.bloqueado:
            motivo = self.motivo_bloqueio or "Cliente bloqueado para vendas."
            return False, motivo
        if self.somente_avista:
            return False, "Este cliente só pode comprar à vista."
        if self.limite_credito <= 0:
            return False, "Cliente sem limite de crédito cadastrado."
        if valor_venda > self.limite_disponivel:
            return False, (f"Limite de crédito insuficiente. Disponível: {formatar_moeda_br(self.limite_disponivel)} | Valor da venda: {formatar_moeda_br(valor_venda)}")
        return True, "OK"

    # ── Save / Meta ──────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        self.razao_social = self.razao_social.strip().upper()
        self.fantasia = self.fantasia.strip().upper()
        self.endereco = self.endereco.strip().upper()
        self.complem = self.complem.strip().upper()
        self.email = self.email.strip().lower()
        if self._state.adding and self.vinc_emp_id and not self.codigo:
            with transaction.atomic():
                ult = (Cliente.objects.select_for_update().filter(vinc_emp_id=self.vinc_emp_id).aggregate(max_codigo=models.Max('codigo'))['max_codigo'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.fantasia}"

    class Meta:
        verbose_name_plural = "Clientes"
        constraints = [
            models.UniqueConstraint(fields=['cpf_cnpj', 'vinc_emp'], name='unique_cpf_cnpj_cliente_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_cliente_empresa')
        ]

class CreditoCliente(models.Model):
    SITUACAO = [('Aberto', 'Aberto'),('Utilizado', 'Utilizado'),('Cancelado', 'Cancelado'),]
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey('empresas.Empresa',on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial',on_delete=models.PROTECT)
    cliente = models.ForeignKey('clientes.Cliente',on_delete=models.PROTECT,related_name='creditos')
    pedido_origem = models.ForeignKey('pedidos.Pedido',on_delete=models.PROTECT,related_name='creditos_gerados')
    pedido_utilizado = models.ForeignKey('pedidos.Pedido',on_delete=models.PROTECT,null=True,blank=True,related_name='creditos_utilizados')
    usuario = models.ForeignKey('filiais.Usuario',on_delete=models.SET_NULL,null=True)
    valor = models.DecimalField(max_digits=12,decimal_places=2)
    saldo = models.DecimalField(max_digits=12,decimal_places=2)
    situacao = models.CharField(max_length=10,choices=SITUACAO,default='Aberto')
    observacao = models.TextField(blank=True)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'Crédito de Cliente'
        verbose_name_plural = 'Créditos de Clientes'

    def __str__(self):
        return f'{self.cliente} - Saldo: R$ {self.saldo}'
