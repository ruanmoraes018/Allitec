from django import forms
from .models import Empresa

class EmpresaForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    principal = forms.ChoiceField(label="Principal?", choices=[('Sim', 'Sim'), ('Não', 'Não')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    dia_venc = forms.ChoiceField(label="Dia Venc.", choices=[('05', '05'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cnpj = forms.CharField(label='CNPJ',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    ie = forms.CharField(label='Inscrição Estadual', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    razao_social = forms.CharField(label='Razão Social',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    bairro_emp = forms.CharField(label='Bairro',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    complem = forms.CharField(label='Complemento', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cidade_emp = forms.CharField(label='Cidade',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    uf_emp = forms.CharField(label='Estado',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    numero = forms.CharField(label='Nº',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))

    gerar_filial = forms.BooleanField(required=False, label="Gerar Filial?", widget=forms.CheckboxInput())

    nome = forms.CharField(label='Nome do Responsável',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cpf = forms.CharField(label='CPF',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    orgao = forms.CharField(label='Órgão Emissor',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    dt_nasc = forms.CharField(label="Data de Nascimento",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco_adm = forms.CharField(label="Endereço",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep_adm = forms.CharField(label="CEP",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    numero_adm = forms.CharField(label="Nº",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    bairro_adm = forms.CharField(label="Bairro",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cidade_adm = forms.CharField(label="Cidade",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    uf_adm = forms.CharField(label="UF",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    tel_adm = forms.CharField(label="Fone",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    email_adm = forms.CharField(label="E-mail",
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))

    qtd_filial = forms.IntegerField(label='Quantidade de Filiais', min_value=1,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    qtd_usuarios = forms.IntegerField(label='Quantidade de Usuários', min_value=1,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))


    class Meta:
        model = Empresa
        fields = (
            'situacao', 'gerar_filial', 'cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro_emp', 'cidade_emp', 'uf_emp', 'tel', 'email',
            'logo', 'nome', 'cpf', 'orgao', 'dt_nasc', 'endereco_adm', 'cep_adm', 'numero_adm', 'bairro_adm', 'cidade_adm', 'uf_adm', 'principal',
            'tel_adm', 'email_adm', 'dia_venc', 'qtd_filial', 'qtd_usuarios'
        )
