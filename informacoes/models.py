from django.db import models
from django.db import transaction

class Informacoes(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    conteudo = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.empresa and not self.codigo:
            with transaction.atomic():
                ult = (Informacoes.objects.select_for_update().filter(empresa=self.empresa).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                self.descricao = self.descricao.strip().upper()
                super().save(*args, **kwargs)
        else:
            self.descricao = self.descricao.strip().upper()
            super().save(*args, **kwargs)
    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Informações"
        constraints = [
            models.UniqueConstraint(fields=['descricao', 'empresa'], name='unique_informacoes_por_empresa'),
            models.UniqueConstraint(fields=['codigo', 'empresa'], name='unique_codigo_informacoes_empresa')
        ]