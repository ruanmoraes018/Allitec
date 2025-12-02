from django.db import models
import unicodedata
from filiais.models import Filial

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Grupo(models.Model):
    nome_grupo = models.CharField(
        max_length=100,
        verbose_name="Descrição"
    )
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.nome_grupo = remove_accents(self.nome_grupo).lower()
        self.nome_grupo = self.nome_grupo.upper()
        super(Grupo, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_grupo}"

    class Meta:
        verbose_name_plural = "Grupos"