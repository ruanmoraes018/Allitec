from django.db import models
import unicodedata
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import datetime
from empresas.models import Empresa
from django.contrib.auth.models import AbstractUser
import os
from django.core.exceptions import ValidationError

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])

def data_hoje_formatada():
    return datetime.now().strftime('%d/%m/%Y')

class Filial(models.Model):
    situacao = models.CharField(max_length=10, verbose_name="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')])
    layout_contrato = models.CharField(max_length=10, verbose_name="Layout Contrato", choices=[('Layout 1', 'Layout 1'), ('Layout 2', 'Layout 2')], default="Layout 1")
    tp_chave = models.CharField(max_length=20, verbose_name="Tipo de Chave Pix", choices=[('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('E-mail', 'E-mail'), ('Telefone', 'Telefone'), ('Chave Aleatória', 'Chave Aleatória')])
    chave_pix = models.CharField(max_length=100, verbose_name="Chave Pix")
    banco_fil = models.ForeignKey('bancos.Banco', on_delete=models.SET_NULL, null=True, blank=True)
    beneficiario = models.CharField(max_length=255, verbose_name='Nome Beneficiário')
    info_comp = models.TextField(default="Obrigado pela preferência!", blank=True)
    info_local = models.TextField(default="Atendemos em todo estado do Pará!", blank=True)
    info_orcamento = models.TextField(default="*Caro cliente, caso você encontre um orçamento com valor inferior, podemos analisar o orçamento concorrente para fecharmos negócio.", blank=True)
    cnpj = models.CharField(max_length=20, verbose_name='CNPJ')
    ie = models.CharField(max_length=20, verbose_name='Inscrição Estadual')
    razao_social = models.CharField(max_length=100, verbose_name='Razão Social')
    fantasia = models.CharField(max_length=100, verbose_name='Fantasia')
    endereco = models.CharField(max_length=100, verbose_name='Endereço')
    cep = models.CharField(max_length=10, verbose_name='CEP')
    numero = models.CharField(max_length=10, verbose_name='Nº')
    tb_preco = models.ForeignKey('tabelas_preco.TabelaPreco', on_delete=models.SET_NULL, null=True)
    cli = models.ForeignKey('clientes.Cliente', on_delete=models.SET_NULL, null=True)
    tec = models.ForeignKey('tecnicos.Tecnico', on_delete=models.SET_NULL, null=True)
    bairro_fil = models.ForeignKey('bairros.Bairro', on_delete=models.SET_NULL, null=True)
    complem = models.CharField(max_length=20, verbose_name='Complemento', blank=True)
    cidade_fil = models.ForeignKey('cidades.Cidade', on_delete=models.SET_NULL, null=True)
    uf = models.ForeignKey('estados.Estado', on_delete=models.SET_NULL, null=True)
    tel = models.CharField(max_length=15, verbose_name='Fone')
    email = models.EmailField(max_length=40, verbose_name='E-mail')
    fantasia_normalizado = models.CharField(max_length=255, editable=False)
    logo = models.FileField(upload_to='logo/', null=True, blank=True, default='default_logo.png')
    vinc_emp = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    dt_criacao = models.DateField(verbose_name="Data de Registro", null=True, blank=True, db_index=True)
    dt_inativacao = models.DateField(verbose_name="Data de Inativação", null=True, blank=True, db_index=True)
    max_parcelas = models.PositiveIntegerField(default=1)
    max_dias_intervalo = models.PositiveIntegerField(default=30)
    tp_calc_juros = models.CharField(max_length=15, verbose_name="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], default="Percentual")
    tp_calc_multa = models.CharField(max_length=15, verbose_name="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], default="Percentual")
    ft_multa = models.DecimalField(verbose_name="Fator Multa", max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    ft_juros = models.DecimalField(verbose_name="Fator Juros",max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    principal = models.BooleanField(default=False, verbose_name='Filial Principal')
    vinculada_a = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='filiais_secundarias', verbose_name='Filial Vinculada à')
    def save(self, *args, **kwargs):
        self.cnpj = self.cnpj.upper()
        self.ie = self.ie.upper()
        self.razao_social = self.razao_social.upper()
        self.fantasia = self.fantasia.upper()
        self.beneficiario = self.beneficiario.upper()
        self.endereco = self.endereco.upper()
        self.cep = self.cep.upper()
        self.numero = self.numero.upper()
        self.complem = self.complem.upper()
        self.tel = self.tel.upper()
        self.email = self.email.lower()
        self.fantasia_normalizado = remove_accents(self.fantasia).lower()
        logo_alterada = False
        super().save(*args, **kwargs)
        if self.logo and self.logo.name != 'default_logo.png':
            img = Image.open(self.logo.path)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            max_size = (300, 300)
            img.thumbnail(max_size)
            img_io = BytesIO()
            img.save(img_io, format='PNG', quality=90)
            novo_nome = f'logo_{self.pk}.png'
            self.logo.save(novo_nome, ContentFile(img_io.getvalue()), save=False)
            logo_alterada = True
        if logo_alterada:
            super().save(update_fields=['logo'])

    def clean(self):
        if self.principal:
            qs = Filial.objects.filter(vinc_emp=self.vinc_emp, principal=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Já existe uma filial principal para esta empresa.")
    def __str__(self):
        return f"{self.fantasia}"

    class Meta:
        verbose_name_plural = "Filiais"

class Usuario(AbstractUser):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="usuarios", null=True, blank=True)
    username = models.CharField(max_length=150)
    filial_user = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True, related_name="usuarios")
    codigo_local = models.PositiveIntegerField(blank=True, null=True)
    gerar_senha_lib = models.BooleanField(default=False, verbose_name='Gerar Senha de Liberação')
    senha_liberacao = models.CharField(max_length=20, blank=True, null=True, verbose_name='Senha de Liberação')
    is_master = models.BooleanField(default=False)

    class Meta:
        unique_together = ('username', 'empresa')

    def save(self, *args, **kwargs):
        if self.empresa and not self.codigo_local:
            ultimo = Usuario.objects.filter(empresa=self.empresa).aggregate(
                models.Max('codigo_local')
            )['codigo_local__max'] or 0
            self.codigo_local = ultimo + 1
        super().save(*args, **kwargs)

    def __str__(self):
        if self.empresa:
            if self.filial_user:
                return f"{self.username} - Emp: {self.empresa.fantasia}/Filial P.: {self.filial_user.fantasia}"
            return f"{self.username} - Emp: {self.empresa.fantasia}"
        return f"{self.username} (GLOBAL)"
