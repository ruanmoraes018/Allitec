from django.db import models

class Bairro(models.Model):
    nome_bairro = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.nome_bairro = self.nome_bairro.strip().upper()
        super(Bairro, self).save(*args, **kwargs)

    def __str__(self):
        return self.nome_bairro

    class Meta:
        verbose_name_plural = "Bairros"
        constraints = [
            models.UniqueConstraint(fields=['nome_bairro', 'vinc_emp'], name='unique_bairro_por_empresa')
        ]