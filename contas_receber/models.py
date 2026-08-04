from django.db import models
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.db import transaction

class ContaReceber(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.SET_NULL, null=True)
    SITUACAO = [('Aberta', 'Aberta'), ('Paga', 'Paga')]
    # Origem
    orcamento = models.ForeignKey('orcamentos.Orcamento', on_delete=models.SET_NULL, null=True, blank=True, related_name='titulos_orc')
    pedido = models.ForeignKey('pedidos.Pedido', on_delete=models.SET_NULL, null=True, blank=True, related_name='titulos_pedidos')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='contas_receber_orc')
    forma_pgto = models.ForeignKey('formas_pgto.FormaPgto', on_delete=models.PROTECT, null=True, blank=True)
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
        verbose_name_plural = "Contas à Receber"
        permissions = [
            ("atribuir_desconto_cr", "Pode aplicar descontos em contas à pagar"),
            ("baixar_cr", "Pode realizar baixa em contas à pagar"),
            ("estornar_cr", "Pode realizar estorno em contas à pagar"),
        ]
        constraints = [models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_conta_receber_empresa')]
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (ContaReceber.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
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
    @transaction.atomic
    def baixar(self, pagamentos, juros=Decimal("0.00"), multa=Decimal("0.00"), desconto=Decimal("0.00")):
        if self.situacao == "Paga":
            raise ValueError("Título já está pago.")
        self.juros = juros
        self.multa = multa
        self.desconto = desconto
        total_titulo = self.valor + juros + multa - desconto
        total_pago = Decimal("0.00")
        for pagamento in pagamentos:
            ContaReceberBaixaForma.objects.create(vinc_emp=self.vinc_emp, conta_receber=self,
                forma_pgto=pagamento["forma_pgto"], valor=pagamento["valor"]
            )
            total_pago += pagamento["valor"]
        self.valor_pago = total_pago
        self.data_pagamento = timezone.now().date()
        saldo = total_titulo - total_pago
        if saldo > Decimal("0.00"):
            ContaReceber.objects.create(vinc_emp=self.vinc_emp, vinc_fil=self.vinc_fil, orcamento=self.orcamento, pedido=self.pedido, cliente=self.cliente, forma_pgto=None,
                num_conta=self.num_conta, titulo_origem=self, tipo="Remanescente", tp_juros=self.tp_juros, tp_multa=self.tp_multa, valor=saldo, valor_pago=Decimal("0.00"),
                juros=self.juros, multa=self.multa, desconto=Decimal("0.00"), data_emissao=self.data_emissao, data_vencimento=self.data_vencimento, situacao="Aberta",
                obs_internas=f"Saldo remanescente do título {self.num_conta}"
            )
        self.situacao = "Paga"
        if len(pagamentos) == 1: self.forma_pgto = pagamentos[0]["forma_pgto"]
        else: self.forma_pgto = None
        self.save()
        return saldo
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
        # Remove as formas de pagamento desta baixa
        self.formas_baixa.all().delete()
        # Restaura o título
        self.situacao = "Aberta"
        self.valor_pago = Decimal("0.00")
        self.data_pagamento = None
        self.forma_pgto = None
        # Se esses valores são definidos na baixa
        self.juros = Decimal("0.00")
        self.multa = Decimal("0.00")
        self.desconto = Decimal("0.00")
        self.save()
        return self
    
class ContaReceberBaixaForma(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    conta_receber = models.ForeignKey(ContaReceber, on_delete=models.CASCADE, related_name='formas_baixa')
    forma_pgto = models.ForeignKey('formas_pgto.FormaPgto', on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Forma de pagamento da baixa'
        verbose_name_plural = 'Formas de pagamento da baixa'

    def __str__(self):
        return f'{self.conta_receber.num_conta} - {self.forma_pgto} - {self.valor}'