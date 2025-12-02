from django.db import models

class TabelaPreco(models.Model):
    descricao = models.CharField(max_length=100, unique=True)
    margem = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        super(TabelaPreco, self).save(*args, **kwargs)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Tabelas de Preço"