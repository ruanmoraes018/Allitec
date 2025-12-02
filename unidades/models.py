from django.db import models
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Unidade(models.Model):
    nome_unidade = models.CharField(max_length=100, unique=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.nome_unidade = self.nome_unidade.upper()
        super(Unidade, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome_unidade

    class Meta:
        verbose_name_plural = "Unidades"
