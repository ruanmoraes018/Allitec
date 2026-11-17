from django.db import models
import unicodedata
from django.db import transaction

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Banco(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    nome_banco = models.CharField(max_length=100, verbose_name="Nome")
    cod_banco = models.CharField(max_length=100, verbose_name="Código Banco")
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.nome_banco = self.nome_banco.strip().upper()
        if self._state.adding and self.vinc_emp_id and not self.codigo:
            with transaction.atomic():
                ult = (Banco.objects.select_for_update().filter(vinc_emp_id=self.vinc_emp_id).aggregate(max_codigo=models.Max('codigo'))['max_codigo'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.cod_banco} - {self.nome_banco}"

    class Meta:
        verbose_name_plural = "Bancos"
        constraints = [
            models.UniqueConstraint(fields=['nome_banco', 'vinc_emp'], name='unique_banco_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_banco_empresa')
        ]