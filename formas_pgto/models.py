from django.db import models

class FormaPgto(models.Model):
    descricao = models.CharField(max_length=100, unique=True)
    situacao = models.CharField(
        max_length=7,
        verbose_name="Situação",
        choices=[
            ('Ativo', 'Ativo'),
            ('Inativo', 'Inativo')
        ]
    )
    troco = models.CharField(
        max_length=3,
        verbose_name="Permite troco?",
        choices=[
            ('Sim', 'Sim'),
            ('Não', 'Não')
        ]
    )
    tipo = models.CharField(
        max_length=8,
        verbose_name="Tipo da Forma",
        choices=[
            ('A vista', 'A vista'),
            ('A prazo', 'A prazo')
        ]
    )
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        super(FormaPgto, self).save(*args, **kwargs)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Formas de Pagamento"