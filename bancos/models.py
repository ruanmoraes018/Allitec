from django.db import models
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

class Banco(models.Model):
    nome_banco = models.CharField(
        max_length=100,
        verbose_name="Nome"
    )
    cod_banco = models.CharField(
        max_length=100,
        verbose_name="Código Banco"
    )
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.banco_normalizado = remove_accents(self.nome_banco).lower()
        self.nome_banco = self.banco_normalizado
        self.nome_banco = self.nome_banco.upper()
        super(Banco, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.cod_banco} - {self.nome_banco}"

    class Meta:
        verbose_name_plural = "Bancos"