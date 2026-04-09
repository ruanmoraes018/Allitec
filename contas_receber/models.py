from django.db import models
from decimal import Decimal
from datetime import date

class ContaReceber(models.Model):
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
    data_emissao = models.DateField(auto_now_add=True)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    situacao = models.CharField(max_length=14, choices=SITUACAO, default='Aberta')
    observacao = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name_plural = "Contas à Receber"
        permissions = [
            ("atribuir_desconto_cr", "Pode aplicar descontos em contas à pagar"),
            ("baixar_cr", "Pode realizar baixa em contas à pagar"),
            ("estornar_cr", "Pode realizar estorno em contas à pagar"),
        ]
    def save(self, *args, **kwargs):
        self.num_conta = self.num_conta.upper()
        super(ContaReceber, self).save(*args, **kwargs)
    @property
    def saldo(self):
        """Quanto ainda falta pagar"""
        total_corrigido = self.valor + self.juros + self.multa - self.desconto
        return total_corrigido - self.valor_pago
    @property
    def esta_vencido(self):
        if self.situacao == 'Paga':
            return False
        return date.today() > self.data_vencimento
    @property
    def dias_atraso(self):
        if not self.esta_vencido:
            return 0
        return (date.today() - self.data_vencimento).days
    @property
    def valor_juros(self):
        if self.dias_atraso <= 0:
            return Decimal('0.00')
        if not self.juros:
            return Decimal('0.00')
        if self.tp_juros == 'Percentual':
            return (self.valor * (self.juros / Decimal('100')) * self.dias_atraso)
        else:
            return self.juros * self.dias_atraso
    @property
    def valor_multa(self):
        if self.dias_atraso <= 0:
            return Decimal('0.00')
        if not self.multa:
            return Decimal('0.00')
        if self.tp_multa == 'Percentual':
            return self.valor * (self.multa / Decimal('100'))
        else:
            return self.multa
    @property
    def valor_total(self):
        return self.valor + self.valor_multa + self.valor_juros
    def __str__(self):
        return f"{self.num_conta}"

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