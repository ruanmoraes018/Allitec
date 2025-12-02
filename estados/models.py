from django.db import models

class Estado(models.Model):
    nome_estado = models.CharField(max_length=100, unique=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.nome_estado = self.nome_estado.strip().upper()
        super(Estado, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome_estado

    class Meta:
        verbose_name_plural = "Estados"