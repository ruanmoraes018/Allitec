from django.db import models
from django.db import transaction

# Create your models here.
class Estoque(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    filial = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE, related_name='estoques')
    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        if self._state.adding and self.vinc_emp_id and not self.codigo:
            with transaction.atomic():
                ult = (Estoque.objects.select_for_update().filter(vinc_emp_id=self.vinc_emp_id).aggregate(max_codigo=models.Max('codigo'))['max_codigo'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)
    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Estoques"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'empresa'], name='unique_estoque_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'empresa'], name='unique_codigo_estoque_empresa')
        ]