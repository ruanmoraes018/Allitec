from django.db import models
import unicodedata
from django.db import transaction

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Unidade(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    nome_unidade = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (Unidade.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.nome_unidade = self.nome_unidade.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.nome_unidade = self.nome_unidade.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.nome_unidade
    class Meta:
        verbose_name_plural = "Unidades"
        constraints = [
            models.UniqueConstraint(fields=['nome_unidade', 'vinc_emp'], name='unique_unidade_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_unidade_empresa')
        ]