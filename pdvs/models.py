from django.db import models
from django.db import transaction

class PDV(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)  # Ex: PDV 1, PDV 2
    situacao = models.CharField(choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], default='Ativo', max_length=10)
    def __str__(self):
        return self.nome
    def save(self, *args, **kwargs):
        if self.vinc_emp and not self.codigo:
            with transaction.atomic():
                ult = (PDV.objects.select_for_update().filter(vinc_emp=self.vinc_emp).aggregate(models.Max('codigo'))['codigo__max'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
    class Meta:
        verbose_name_plural = "Pontos de Venda"
        constraints = [models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_pdv_empresa')]