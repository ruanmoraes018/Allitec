from django.db import models
from django.db import transaction

class Cidade(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    nome_cidade = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        self.nome_cidade = self.nome_cidade.strip().upper()
        if self._state.adding and self.vinc_emp_id and not self.codigo:
            with transaction.atomic():
                ult = (Cidade.objects.select_for_update().filter(vinc_emp_id=self.vinc_emp_id).aggregate(max_codigo=models.Max('codigo'))['max_codigo'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)
    def __str__(self):
        return self.nome_cidade

    class Meta:
        verbose_name_plural = "Cidades"
        constraints = [
            models.UniqueConstraint(fields=['nome_cidade', 'vinc_emp'], name='unique_cidade_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_cidade_empresa')
        ]