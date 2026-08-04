from django.db import models
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.db import transaction

class ContaPagar(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    filial = models.ForeignKey('filiais.Filial', on_delete=models.SET_NULL, null=True)
    SITUACAO = [('Aberta', 'Aberta'), ('Paga', 'Paga')]
    STATUS = [('Ativo', 'Ativo'), ('Inativo', 'Inativo')]
    # Origem
    fornecedor = models.ForeignKey('fornecedores.Fornecedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='titulos_fornecedores')
    # Identificação da parcela
    num_conta = models.CharField(max_length=50, verbose_name="Nº Conta", null=True, blank=True)
    # Valores
    tp_juros = models.CharField(max_length=15, verbose_name="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], default="Percentual")
    tp_multa = models.CharField(max_length=15, verbose_name="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], default="Percentual")
    valor = models.DecimalField(max_digits=12, decimal_places=2)  # valor original
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    juros = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    multa = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    # Datas
    data_emissao = models.DateField()
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    situacao = models.CharField(max_length=14, choices=SITUACAO, default='Aberta')
    status = models.CharField(max_length=14, choices=STATUS, default='Ativo')
    observacao = models.TextField(blank=True, null=True)
    obs_internas = models.TextField(blank=True, null=True)

    motivo = models.TextField(blank=True, null=True, default="")
    titulo_origem = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="titulos_remanescentes"
    )
    TIPOS = [
        ("Original", "Original"),
        ("Remanescente", "Remanescente"),
    ]
    tipo = models.CharField(
        max_length=15,
        choices=TIPOS,
        default="Original"
    )
    class Meta:
        verbose_name_plural = "Contas à Pagar"
        permissions = [
            ("baixar_cp", "Pode realizar baixa em contas à pagar"),
            ("estornar_cp", "Pode realizar estorno em contas à pagar"),
        ]
        constraints = [
            models.UniqueConstraint(fields=['codigo', 'empresa'], name='unique_codigo_contas_pagar_empresa')
        ]
    def save(self, *args, **kwargs):
        if self.empresa and not self.codigo:
            with transaction.atomic():
                ult = (ContaPagar.objects.select_for_update().filter(empresa=self.empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.num_conta = self.num_conta.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.num_conta = self.num_conta.strip().upper()
            super().save(*args, **kwargs)
    @property
    def saldo(self):
        """Quanto ainda falta pagar"""
        total_corrigido = self.valor + self.juros + self.multa - self.desconto
        return total_corrigido - self.valor_pago
    @property
    def esta_vencido(self):
        if self.situacao == 'Paga': return False
        return date.today() > self.data_vencimento
    @property
    def dias_atraso(self):
        if not self.esta_vencido: return 0
        return (date.today() - self.data_vencimento).days
    @property
    def valor_juros(self):
        if self.dias_atraso <= 0: return Decimal('0.00')
        if not self.juros: return Decimal('0.00')
        if self.tp_juros == 'Percentual': return (self.valor * (self.juros / Decimal('100')) * self.dias_atraso)
        else: return self.juros * self.dias_atraso
    @property
    def valor_multa(self):
        if self.dias_atraso <= 0: return Decimal('0.00')
        if not self.multa: return Decimal('0.00')
        if self.tp_multa == 'Percentual': return self.valor * (self.multa / Decimal('100'))
        else: return self.multa
    @property
    def valor_total(self):
        return self.valor + self.valor_multa + self.valor_juros
    def __str__(self):
        return f"{self.num_conta}"
    def _excluir_remanescentes(self):
        for filho in self.titulos_remanescentes.all():
            if filho.situacao == "Paga":
                raise ValueError("Existem baixas posteriores. Estorne-as primeiro.")
            filho._excluir_remanescentes()
            filho.delete()
    @transaction.atomic
    def estornar(self):
        if self.situacao == "Aberta":
            raise ValueError("Contas à receber abertas não podem ser estornadas.")
        # Exclui todos os remanescentes (recursivamente)
        self._excluir_remanescentes()
        # Restaura o título
        self.situacao = "Aberta"
        self.valor_pago = Decimal("0.00")
        self.data_pagamento = None
        # Se esses valores são definidos na baixa
        self.juros = Decimal("0.00")
        self.multa = Decimal("0.00")
        self.desconto = Decimal("0.00")
        self.save()
        return self