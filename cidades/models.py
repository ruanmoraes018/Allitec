from django.db import models
from django.db import transaction

class Cidade(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    nome_cidade = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Cidade.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.nome_cidade = self.nome_cidade.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.nome_cidade = self.nome_cidade.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.nome_cidade

    class Meta:
        verbose_name_plural = "Cidades"
        constraints = [
            models.UniqueConstraint(fields=['nome_cidade', 'vinc_emp'], name='unique_cidade_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_cidade_empresa')
        ]