from django.db import models
from django.db import transaction

class __MODELO__(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (__MODELO__.objects.select_for_update().filter(empresa=self.empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.descricao = self.descricao.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.descricao = self.descricao.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "__MODELO_PLURAL__"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'empresa'], name='unique___MODELO_MINUSCULO___por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'empresa'], name='unique_codigo___MODELO_MINUSCULO___empresa')
        ]