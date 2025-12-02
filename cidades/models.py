from django.db import models

class Cidade(models.Model):
    nome_cidade = models.CharField(max_length=100, unique=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.nome_cidade = self.nome_cidade.strip().upper()
        super(Cidade, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome_cidade

    class Meta:
        verbose_name_plural = "Cidades"
