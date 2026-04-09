from django.db import models

class TabelaPreco(models.Model):
    descricao = models.CharField(max_length=100)
    margem = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tipo = models.CharField(max_length=8, choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')], default='A prazo', verbose_name="Tipo de Plano")
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        super(TabelaPreco, self).save(*args, **kwargs)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Tabelas de Preço"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'vinc_emp'], name='unique_descricao_por_empresa')
        ]