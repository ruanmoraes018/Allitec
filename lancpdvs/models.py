from django.db import models
from django.db import transaction
class Caixa(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
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
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Caixa.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
        else: super().save(*args, **kwargs)
    class Meta:
        verbose_name_plural = "Lançamento de Caixas"
        permissions = [
            ("caixa_outro_user", "Pode realizar lançamentos em caixas de outros usuários"),
        ]
        constraints = [models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_caixa_empresa')]
    @property
    def formas_convertidas(self):
        return [{"descricao": fp.forma_pgto.descricao, "valor": fp.valor} for fp in self.forma_pagamento.select_related("fechamentos").all()]

class CaixaMovimento(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name="movimentos")
    pedido = models.ForeignKey('pedidos.Pedido', null=True, blank=True, on_delete=models.SET_NULL)
    situacao = models.CharField(max_length=10, choices=[('Ativo', 'Ativo'), ('Cancelado', 'Cancelado')], default="Ativo")
    tipo = models.CharField(max_length=10, choices=[('Entrada', 'Entrada'), ('Saída', 'Saída')])
    categoria = models.CharField(max_length=20, choices=[('Venda', 'Venda'), ('Sangria', 'Sangria'), ('Suprimento', 'Suprimento'), ('Saldo Inicial', 'Saldo Inicial'),])
    forma_pagamento = models.ForeignKey('formas_pgto.FormaPgto', on_delete=models.PROTECT)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey('filiais.Usuario', on_delete=models.SET_NULL, null=True)
    def save(self, *args, **kwargs):
        if self.caixa.situacao == 'Fechado': raise ValueError("Caixa fechado não pode receber movimentações.")
        if not self.codigo:
            with transaction.atomic():
                ultimo = (
                    CaixaMovimento.objects
                    .select_for_update()
                    .filter(caixa=self.caixa)
                    .aggregate(models.Max('codigo'))['codigo__max']
                    or 0
                )

                self.codigo = ultimo + 1
        super().save(*args, **kwargs)
    class Meta:
        indexes = [models.Index(fields=['caixa', 'tipo']), models.Index(fields=['caixa', 'forma_pagamento']),]
        constraints = [
            models.UniqueConstraint(
                fields=['caixa', 'codigo'],
                name='unique_codigo_movimento_caixa'
            )
        ]

class CaixaFechamento(models.Model):
    caixa = models.ForeignKey(Caixa, on_delete=models.CASCADE, related_name="fechamentos")
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