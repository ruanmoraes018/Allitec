from django.db import models

class TipoCobranca(models.Model):
    descricao = models.CharField(max_length=100)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        super(TipoCobranca, self).save(*args, **kwargs)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Tipos de Cobrança"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'vinc_emp'], name='unique_tipo_cobranca_por_empresa')
        ]