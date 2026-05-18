from django.db import models
from django.db import transaction

# Create your models here.
class Marca(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    nome_marca = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Marca.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.nome_marca = self.nome_marca.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.nome_marca = self.nome_marca.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.nome_marca

    class Meta:
        verbose_name_plural = "Marcas"
        constraints = [
            models.UniqueConstraint(fields=['nome_marca', 'vinc_emp'], name='unique_nome_marca_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_marca_empresa')
        ]
