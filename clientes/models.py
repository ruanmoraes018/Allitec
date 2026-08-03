from django.db import models
from datetime import datetime
import unicodedata
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from django.db import transaction

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

class Cliente(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey("empresas.Empresa", on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey("filiais.Filial", on_delete=models.SET_NULL, null=True)
    situacao = models.CharField(max_length=10, verbose_name="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')])
    pessoa = models.CharField(max_length=10, verbose_name="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')])
    somente_avista = models.BooleanField(default=False, verbose_name='Vender apenas à vista')
    cpf_cnpj = models.CharField(max_length=25)
    ie = models.CharField(max_length=20, blank=True, null=True)
    razao_social = models.CharField(max_length=100)
    fantasia = models.CharField(max_length=100)
    endereco = models.CharField(max_length=100)
    cep = models.CharField(max_length=10)
    numero = models.CharField(max_length=10)
    bairro = models.ForeignKey(Bairro, on_delete=models.SET_NULL, null=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True)
    complem = models.CharField(max_length=30, blank=True, default="")

    avulso = models.CharField(max_length=10, verbose_name="Situação", choices=[('Sim', 'Sim'), ('Não', 'Não')], default="Não")

    tel = models.CharField(max_length=30)
    email = models.EmailField(max_length=40)
    dt_reg = models.DateField(verbose_name="Data de Registro", null=True, blank=True, db_index=True)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Cliente.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.razao_social = self.razao_social.strip().upper()
                self.fantasia = self.fantasia.strip().upper()
                self.endereco = self.endereco.strip().upper()
                self.complem = self.complem.strip().upper()
                self.email = self.email.strip().lower()
                super().save(*args, **kwargs)
        else:
            self.razao_social = self.razao_social.strip().upper()
            self.fantasia = self.fantasia.strip().upper()
            self.endereco = self.endereco.strip().upper()
            self.complem = self.complem.strip().upper()
            self.email = self.email.strip().lower()
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
    SITUACAO = [
        ('Aberto', 'Aberto'),
        ('Utilizado', 'Utilizado'),
        ('Cancelado', 'Cancelado'),
    ]

    codigo = models.PositiveIntegerField(blank=True, null=True)

    vinc_emp = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE
    )

    vinc_fil = models.ForeignKey(
        'filiais.Filial',
        on_delete=models.PROTECT
    )

    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='creditos'
    )

    pedido_origem = models.ForeignKey(
        'pedidos.Pedido',
        on_delete=models.PROTECT,
        related_name='creditos_gerados'
    )

    pedido_utilizado = models.ForeignKey(
        'pedidos.Pedido',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='creditos_utilizados'
    )

    usuario = models.ForeignKey(
        'filiais.Usuario',
        on_delete=models.SET_NULL,
        null=True
    )

    valor = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    saldo = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    situacao = models.CharField(
        max_length=10,
        choices=SITUACAO,
        default='Aberto'
    )

    observacao = models.TextField(
        blank=True
    )

    data = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-data']
        verbose_name = 'Crédito de Cliente'
        verbose_name_plural = 'Créditos de Clientes'

    def __str__(self):
        return f'{self.cliente} - Saldo: R$ {self.saldo}'
