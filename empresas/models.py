from django.db import models
import unicodedata
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


class Empresa(models.Model):
    situacao = models.CharField(
        max_length=10,
        verbose_name="Situação",
        choices=[
            ('Ativa', 'Ativa'),
            ('Inativa', 'Inativa')
        ]
    )
    principal = models.CharField(
        max_length=10,
        verbose_name="Principal?",
        choices=[
            ('Sim', 'Sim'),
            ('Não', 'Não')
        ],
        default="Não"
    )
    cnpj = models.CharField(max_length=20, verbose_name='CNPJ')
    ie = models.CharField(max_length=20, verbose_name='Inscrição Estadual')
    razao_social = models.CharField(max_length=100, verbose_name='Razão Social')
    fantasia = models.CharField(max_length=100, verbose_name='Fantasia')
    endereco = models.CharField(max_length=100, verbose_name='Endereço')
    cep = models.CharField(max_length=10, verbose_name='CEP')
    numero = models.CharField(max_length=10, verbose_name='Nº')
    bairro_emp = models.CharField(max_length=20, verbose_name='Bairro')
    complem = models.CharField(max_length=20, verbose_name='Complemento', blank=True)
    cidade_emp = models.CharField(max_length=30, verbose_name='Cidade')
    uf_emp = models.CharField(max_length=2, verbose_name='UF')
    tel = models.CharField(max_length=15, verbose_name='Fone')
    email = models.EmailField(max_length=40, verbose_name='E-mail')
    fantasia_normalizado = models.CharField(max_length=255, editable=False)
    nome = models.CharField(max_length=100, verbose_name='Nome Responsável')
    cpf = models.CharField(max_length=15, verbose_name='CPF')
    orgao = models.CharField(max_length=30, verbose_name='Órgão Emissor')
    dt_nasc = models.CharField(max_length=20, verbose_name='Data de Nascimento')
    endereco_adm = models.CharField(max_length=100, verbose_name='Endereço')
    cep_adm = models.CharField(max_length=10, verbose_name='CEP')
    numero_adm = models.CharField(max_length=10, verbose_name='Nº')
    bairro_adm = models.CharField(max_length=20, verbose_name='Bairro')
    cidade_adm = models.CharField(max_length=30, verbose_name='Cidade')
    uf_adm = models.CharField(max_length=2, verbose_name='UF')
    tel_adm = models.CharField(max_length=15, verbose_name='Fone')
    email_adm = models.EmailField(max_length=40, verbose_name='E-mail')
    logo = models.FileField(upload_to='logo/', null=True, blank=True, default='default_logo.png')
    DIA_VENC_CHOICES = [
        ('05', '05'), ('10', '10'), ('15', '15'),
        ('20', '20'), ('25', '25'), ('30', '30')
    ]
    dia_venc = models.CharField(
        max_length=10,
        choices=DIA_VENC_CHOICES,
        default='05'
    )
    dt_criacao = models.DateField(
        verbose_name='Data de Registro',
        auto_now_add=True
    )
    dt_inativacao = models.DateField(verbose_name='Data de Inativação', blank=True, null=True)

    qtd_filial = models.PositiveIntegerField(default=1, verbose_name='Quantidade de Filiais Ativas')
    qtd_usuarios = models.PositiveIntegerField(default=1, verbose_name='Quantidade de Usuários Ativos')

    gerar_filial = models.BooleanField(default=False, verbose_name='Gerar Filial?')
    # vinculada_a = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='filiais_secundarias', verbose_name='Filial Vinculada à')
    def save(self, *args, **kwargs):
        self.cnpj = self.cnpj.upper()
        self.ie = self.ie.upper()
        self.razao_social = self.razao_social.upper()
        self.fantasia = self.fantasia.upper()
        self.endereco = self.endereco.upper()
        self.cep = self.cep.upper()
        self.numero = self.numero.upper()
        self.bairro_emp = self.bairro_emp.upper()
        self.complem = self.complem.upper()
        self.cidade_emp = self.cidade_emp.upper()
        self.uf_emp = self.uf_emp.upper()
        self.tel = self.tel.upper()
        self.email = self.email.lower()
        self.nome = self.nome.upper()
        self.cpf = self.cpf.upper()
        self.orgao = self.orgao.upper()
        self.dt_nasc = self.dt_nasc.upper()
        self.endereco_adm = self.endereco_adm.upper()
        self.cep_adm = self.cep_adm.upper()
        self.numero_adm = self.numero_adm.upper()
        self.bairro_adm = self.bairro_adm.upper()
        self.cidade_adm = self.cidade_adm.upper()
        self.uf_adm = self.uf_adm.upper()
        self.tel_adm = self.tel_adm.upper()
        self.email_adm = self.email_adm.lower()
        self.fantasia_normalizado = remove_accents(self.fantasia).lower()
        self.fantasia = self.fantasia_normalizado.upper()
        if self.logo and self.logo.name != 'media/default_logo.png':  # Ignorar o redimensionamento da logo padrão
            # Abrir a imagem da logo
            img = Image.open(self.logo)

            # Definir o tamanho desejado para a logo
            max_size = (300, 300)  # Redimensionar para 300x300 (ajustável)

            # Redimensionar a imagem mantendo a proporção
            img.thumbnail(max_size)

            # Salvar a nova imagem redimensionada em um arquivo temporário
            img_io = BytesIO()
            img.save(img_io, format='PNG')  # Salve no formato desejado, aqui 'PNG'
            img_content = ContentFile(img_io.getvalue(), name=f'{self.id}.png')
        super(Empresa, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} - {self.fantasia.upper()}"

    class Meta:
        verbose_name_plural = "Empresas"