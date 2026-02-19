from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
from decimal import Decimal

class Mensalidade(models.Model):
    SITUACAO_CHOICES = [
        ('Aberta', 'Aberta'),
        ('Baixada', 'Baixada')
    ]

    TIPO_PAGAMENTO_CHOICES = [
        ('Boleto', 'Boleto'),
        ('Pix', 'Pix')
    ]

    situacao = models.CharField(
        max_length=10,
        choices=SITUACAO_CHOICES,
        default='Aberta'
    )
    num_mens = models.CharField(max_length=10, verbose_name="Nr. Mensalidade", null=True, blank=True)
    dt_venc = models.DateField()
    dt_pag = models.DateField(null=True, blank=True)

    tp_mens = models.CharField(
        max_length=10,
        choices=TIPO_PAGAMENTO_CHOICES,
        default='Pix'
    )
    vl_mens = models.DecimalField(max_digits=10, decimal_places=2)
    vl_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tp_juros = models.CharField(
        max_length=15,
        verbose_name="Tp. Cálculo Juros",
        choices=[
            ('Percentual', 'Percentual'),
            ('Valor', 'Valor')
        ],
        default="Percentual"
    )

    tp_multa = models.CharField(
        max_length=15,
        verbose_name="Tp. Cálculo Multa",
        choices=[
            ('Percentual', 'Percentual'),
            ('Valor', 'Valor')
        ],
        default="Percentual"
    )
    vl_multa = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    vl_juros = models.DecimalField(max_digits=10, decimal_places=2, default=0, null=True, blank=True)

    codigo_boleto = models.CharField(max_length=100, blank=True, null=True)
    pix_txid = models.CharField(max_length=100, blank=True, null=True)

    pix_cobranca_id = models.CharField(max_length=120, null=True, blank=True)

    obs = models.TextField(blank=True, null=True)

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    contrato = models.ForeignKey('contratos.Contrato', on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def atrasada(self):
        return (
            self.situacao == 'Aberta' and
            self.dt_venc is not None and
            self.dt_venc < date.today()
        )

    @property
    def dias_atraso(self):
        if self.situacao == 'Aberta' and self.dt_venc and self.dt_venc < date.today():
            return (date.today() - self.dt_venc).days
        return 0

    @property
    def valor_juros(self):
        if self.dias_atraso <= 0:
            return Decimal('0.00')

        if not self.vl_juros:
            return Decimal('0.00')

        if self.tp_juros == 'Percentual':
            return (
                self.vl_mens *
                (self.vl_juros / Decimal('100')) *
                self.dias_atraso
            )
        else:
            return self.vl_juros * self.dias_atraso

    @property
    def valor_multa(self):
        if self.dias_atraso <= 0:
            return Decimal('0.00')

        if not self.vl_multa:
            return Decimal('0.00')

        if self.tp_multa == 'Percentual':
            return self.vl_mens * (self.vl_multa / Decimal('100'))
        else:
            return self.vl_multa

    @property
    def valor_total(self):
        return self.vl_mens + self.valor_multa + self.valor_juros


    def clean(self):
        if self.situacao == 'Baixada' and not self.dt_pag:
            raise ValidationError("Mensalidade baixada precisa de data de pagamento.")

    def __str__(self):
        return f'{self.empresa} - Venc.: {self.dt_venc} - {self.situacao}'

    class Meta:
        verbose_name_plural = "Mensalidades"
        ordering = ['-dt_venc']
        indexes = [
            models.Index(fields=['situacao']),
            models.Index(fields=['dt_venc']),
            models.Index(fields=['empresa']),
        ]

class CobrancaPix(models.Model):
    mp_payment_id = models.CharField(max_length=120, unique=True)
    qr_code = models.TextField()
    qr_code_base64 = models.TextField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    pago = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    mensalidades = models.ManyToManyField(Mensalidade)

