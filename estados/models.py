from django.db import models
from django.db import transaction

class Estado(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    nome_estado = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Estado.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.nome_estado = self.nome_estado.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.nome_estado = self.nome_estado.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.nome_estado

    class Meta:
        verbose_name_plural = "Estados"
        constraints = [
            models.UniqueConstraint(fields=['nome_estado', 'vinc_emp'], name='unique_nome_estado_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_estado_empresa')
        ]