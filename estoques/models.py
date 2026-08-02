from django.db import models
from django.db import transaction

# Create your models here.
class Estoque(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.empresa and not self.codigo:
            with transaction.atomic():
                ult = (Estoque.objects.select_for_update().filter(empresa=self.empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.descricao = self.descricao.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.descricao = self.descricao.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Estoques"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'empresa'], name='unique_estoque_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'empresa'], name='unique_codigo_estoque_empresa')
        ]