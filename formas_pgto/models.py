from django.db import models
from django.core.exceptions import ValidationError
from core.pagamentos.credenciais import CREDENCIAIS_GATEWAY
import json
from django.db import transaction

class FormaPgto(models.Model):
    codigo = models.PositiveIntegerField(blank=True, null=True)
    descricao = models.CharField(max_length=100)
    situacao = models.CharField(max_length=7, choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')])
    troco = models.CharField(max_length=3, choices=[('Sim', 'Sim'), ('Não', 'Não')], default='Não')
    forma_padrao = models.CharField(max_length=3, choices=[('Sim', 'Sim'), ('Não', 'Não')], default='Não')
    tipo = models.CharField(max_length=8, choices=[('A vista', 'A vista'), ('A prazo', 'A prazo')], default='A vista')
    gera_parcelas = models.BooleanField(default=False)
    vinc_emp = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True)
    gateway = models.CharField(max_length=20,choices=[('nenhum','Nenhum'),('mercadopago','Mercado Pago'),('pagseguro','PagSeguro'),('stripe','Stripe'),('pix_direto','Pix Direto'), ('infinitepay', 'InfinitePay'),],default='nenhum')
    credenciais = models.JSONField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.descricao = self.descricao.strip().upper()
        if self._state.adding and self.vinc_emp_id and not self.codigo:
            with transaction.atomic():
                ult = (FormaPgto.objects.select_for_update().filter(vinc_emp_id=self.vinc_emp_id).aggregate(max_codigo=models.Max('codigo'))['max_codigo'] or 0)
                self.codigo = ult + 1
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)

    def clean(self):
        if self.gateway == "nenhum":
            return
        cred = self.credenciais
        if isinstance(cred, str):
            try:
                cred = json.loads(cred)
            except:
                raise ValidationError("Credenciais inválidas")
        if not cred:
            raise ValidationError("Credenciais obrigatórias para este gateway")
        obrigatorios = CREDENCIAIS_GATEWAY.get(self.gateway, [])
        if self.gateway == "pix_direto" and cred.get("ambiente") == "homologacao":
            obrigatorios = [campo for campo in obrigatorios if campo != "certificado_path"]
        faltando = [campo for campo in obrigatorios if campo not in cred or not cred.get(campo)]
        if faltando:
            raise ValidationError(f"Campos obrigatórios faltando: {', '.join(faltando)}")
        self.credenciais = cred

    def get_credencial(self, chave):
        return (self.credenciais or {}).get(chave)

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name_plural = "Formas de Pagamento"
        constraints = [models.UniqueConstraint(fields=['codigo', 'vinc_emp'], name='unique_codigo_formas_empresa')]