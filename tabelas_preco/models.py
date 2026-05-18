from django.db import models
from django.db import transaction

class TabelaPreco(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    margem = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tipo = models.CharField(max_length=8, choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')], default='A prazo', verbose_name="Tipo de Plano")
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (TabelaPreco.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.descricao = self.descricao.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.descricao = self.descricao.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Tabelas de Preço"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'vinc_emp'], name='unique_descricao_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_tabela_empresa')
        ]