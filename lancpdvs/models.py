from django.db import models
class Caixa(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    usuario = models.ForeignKey('filiais.Usuario', on_delete=models.SET_NULL, null=True)
    terminal = models.ForeignKey('pdvs.PDV', on_delete=models.PROTECT)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    situacao = models.CharField(max_length=10, choices=[('Aberto', 'Aberto'), ('Fechado', 'Fechado')], default="Aberto")  # Aberto / Fechado
    observacao = models.TextField(blank=True)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    diferenca = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    @property
    def saldo_inicial(self):
        mov = self.movimentos.filter(categoria='Saldo Inicial').first()
        return mov.valor if mov else 0
    
class CaixaMovimento(models.Model):
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name="movimentos")
    pedido = models.ForeignKey('pedidos.Pedido', null=True, blank=True, on_delete=models.SET_NULL)
    tipo = models.CharField(max_length=10, choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')])
    categoria = models.CharField(max_length=20, choices=[
        ('Venda', 'Venda'),
        ('Sangria', 'Sangria'),
        ('Suprimento', 'Suprimento'),
        ('Saldo Inicial', 'Saldo Inicial'),
    ])
    forma_pagamento = models.ForeignKey('formas_pgto.FormaPgto', on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('filiais.Usuario', on_delete=models.SET_NULL, null=True)
    def save(self, *args, **kwargs):
        if self.caixa.situacao == 'Fechado':
            raise ValueError("Caixa fechado não pode receber movimentações.")
        super().save(*args, **kwargs)
    class Meta:
        indexes = [
            models.Index(fields=['caixa', 'tipo']),
            models.Index(fields=['caixa', 'forma_pagamento']),
        ]
class CaixaFechamento(models.Model):
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE)
    forma_pagamento = models.ForeignKey('formas_pgto.FormaPgto', on_delete=models.PROTECT)
    valor_registrado = models.DecimalField(max_digits=10, decimal_places=2)
    valor_informado = models.DecimalField(max_digits=10, decimal_places=2)
    diferenca = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        unique_together = ('caixa', 'forma_pagamento')

    def save(self, *args, **kwargs):
        if self.caixa.situacao == 'Fechado':
            raise ValueError("Não é permitido alterar movimentos de um caixa fechado.")
        super().save(*args, **kwargs)