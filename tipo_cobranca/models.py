from django.db import models
from django.db import transaction

class TipoCobranca(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (TipoCobranca.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.descricao = self.descricao.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.descricao = self.descricao.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Tipos de Cobrança"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'vinc_emp'], name='unique_tipo_cobranca_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_tipo_empresa')
        ]