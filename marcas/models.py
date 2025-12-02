from django.db import models

# Create your models here.
class Marca(models.Model):
    nome_marca = models.CharField(max_length=100, unique=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.nome_marca = self.nome_marca.strip().upper()
        super(Marca, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome_marca

    class Meta:
        verbose_name_plural = "Marcas"