from django.db import models

class PDV(models.Model):
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    vinc_fil = models.ForeignKey('filiais.Filial', on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)  # Ex: PDV 1, PDV 2
    situacao = models.CharField(choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], default='Ativo', max_length=10)
    def __str__(self):
        return self.nome