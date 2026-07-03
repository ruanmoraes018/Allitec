from django.db import models

# Create your models here.
class Proposta(models.Model):
    STATUS = (('Aberta', 'Aberta'), ('Confirmada', 'Confirmada'),)
    desc_imp = models.CharField(max_length=200)
    qtd_usu = models.IntegerField()
    vl_imp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    dsct_imp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    vl_fin_imp = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    desc_ass = models.CharField(max_length=200)
    vl_ass = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    qtd_ass = models.IntegerField()
    dsct_ass = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    vl_fin_ass = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    dt_emi = models.DateTimeField(null=True, blank=True, db_index=True)
    data_confirmacao = models.DateTimeField(null=True, blank=True, db_index=True)
    nome_emp = models.CharField(max_length=100)
    obs = models.TextField(blank=True, null=True)
    situacao = models.CharField(max_length=10, choices=STATUS,)
    def save(self, *args, **kwargs):
        self.desc_imp = self.desc_imp.upper()
        self.desc_ass = self.desc_ass.upper()
        self.nome_emp = self.nome_emp.upper()
        super(Proposta, self).save(*args, **kwargs)
    def __str__(self):
        return f"Proposta Nº {self.id} - {self.nome_emp}"
    class Meta:
        verbose_name_plural = "Propostas"