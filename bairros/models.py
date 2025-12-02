from django.db import models

# Create your models here.
class Bairro(models.Model):
    nome_bairro = models.CharField(max_length=100, unique=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.nome_bairro = self.nome_bairro.strip().upper()
        super(Bairro, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome_bairro

    class Meta:
        verbose_name_plural = "Bairros"