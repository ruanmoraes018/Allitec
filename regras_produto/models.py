from django.db import models
from django.db import transaction

class RegraProduto(models.Model):
    cod_local = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    produto = models.ForeignKey('produtos.Produto', verbose_name="Produto", null=True, blank=True, on_delete=models.SET_NULL)
    codigo = models.CharField(max_length=50, help_text="Identificador interno da regra (ex: MOTOR, LAMINA, PINTURA)")
    descricao = models.CharField(max_length=100, help_text="Descrição legível da regra")

    tipo = models.CharField(max_length=20, choices=[('QTD', 'Cálculo de Quantidade'), ('SELECAO', 'Seleção Automática'),])
    tipo_regra = models.CharField(max_length=20, null=True, blank=True, choices=[('', ''), ('qtd', 'Quantidade (múltiplos produtos)'), ('peso', 'Por Peso (máx)'), ('simples', 'Valor Simples'),])
    expressao_json = models.JSONField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    class Meta:
        verbose_name_plural = "Regras de Produto"
        constraints = [
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_regra_por_empresa'),
            models.UniqueConstraint(fields=['cod_local', 'vinc_emp'], name='unique_cod_local_regra_empresa')
        ]
    def __str__(self):
        return f"{self.codigo} - {self.descricao}"
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.cod_local:
            with transaction.atomic():
                ult = (RegraProduto.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('cod_local'))['cod_local__max'] or 0)
                self.cod_local = ult + 1
                self.codigo = self.codigo.strip().upper()
                self.descricao = self.descricao.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.codigo = self.codigo.strip().upper()
            self.descricao = self.descricao.strip().upper()
            super().save(*args, **kwargs)