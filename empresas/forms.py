from django import forms
from util.parse_decimal import parse_decimal
from .models import Empresa

s = "form-select form-select-sm border-dark-subtle"
c = "form-control form-control-sm border-dark-subtle"
ct = "form-control form-control-sm border-dark-subtle text-uppercase"
class EmpresaForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativa', 'Ativa'), ('Inativa', 'Inativa')], widget=forms.Select(attrs={'class': s}))
    principal = forms.ChoiceField(label="Principal?", choices=[('Sim', 'Sim'), ('Não', 'Não')], widget=forms.Select(attrs={'class': s}))
    dia_venc = forms.ChoiceField(label="Dia Venc.", choices=[('05', '05'), ('10', '10'), ('15', '15'), ('20', '20'), ('25', '25'), ('30', '30')], widget=forms.Select(attrs={'class': s}))
    cnpj = forms.CharField(label='CNPJ', widget=forms.TextInput(attrs={'class': c}))
    ie = forms.CharField(label='IE', required=False, widget=forms.TextInput(attrs={'class': c}))
    razao_social = forms.CharField(label='Razão Social', widget=forms.TextInput(attrs={'class': ct}))
    fantasia = forms.CharField(label='Fantasia', widget=forms.TextInput(attrs={'class': ct}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': ct}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': c}))
    bairro_emp = forms.CharField(label='Bairro', widget=forms.TextInput(attrs={'class': ct}))
    complem = forms.CharField(label='Complemento', required=False, widget=forms.TextInput(attrs={'class': ct}))
    cidade_emp = forms.CharField(label='Cidade', widget=forms.TextInput(attrs={'class': ct}))
    uf_emp = forms.CharField(label='Estado', widget=forms.TextInput(attrs={'class': ct}))
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': c}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': c}))
    email = forms.CharField(label='E-mail', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    gerar_filial = forms.BooleanField(required=False, label="Gerar Filial?", widget=forms.CheckboxInput())
    nome = forms.CharField(label='Nome do Responsável', widget=forms.TextInput(attrs={'class': ct}))
    cpf = forms.CharField(label='CPF', widget=forms.TextInput(attrs={'class': c}))
    orgao = forms.CharField(label='Órgão Emissor', widget=forms.TextInput(attrs={'class': ct}))
    dt_nasc = forms.CharField(label="Data de Nascimento", widget=forms.TextInput(attrs={'class': ct}))
    endereco_adm = forms.CharField(label="Endereço", widget=forms.TextInput(attrs={'class': ct}))
    cep_adm = forms.CharField(label="CEP", widget=forms.TextInput(attrs={'class': ct}))
    numero_adm = forms.CharField(label="Nº", widget=forms.TextInput(attrs={'class': ct}))
    bairro_adm = forms.CharField(label="Bairro", widget=forms.TextInput(attrs={'class': ct}))
    cidade_adm = forms.CharField(label="Cidade", widget=forms.TextInput(attrs={'class': ct}))
    uf_adm = forms.CharField(label="UF", widget=forms.TextInput(attrs={'class': ct}))
    tel_adm = forms.CharField(label="Fone", widget=forms.TextInput(attrs={'class': ct}))
    email_adm = forms.CharField(label="E-mail", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    qtd_filial = forms.IntegerField(label='Quantidade de Filiais', min_value=1, widget=forms.TextInput(attrs={'class': c}))
    qtd_usuarios = forms.IntegerField(label='Quantidade de Usuários', min_value=1, widget=forms.TextInput(attrs={'class': c}))
    tp_calc_juros = forms.ChoiceField(label="Tp. Cálculo Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': s}))
    tp_calc_multa = forms.ChoiceField(label="Tp. Cálculo Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': s}))
    ft_juros = forms.CharField(label='Fator Juros', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))
    ft_multa = forms.CharField(label='Fator Multa', widget=forms.TextInput(attrs={'class': f'{c} text-end fw-bold'}))

    class Meta:
        model = Empresa
        fields = ('situacao','gerar_filial','cnpj','ie','razao_social','fantasia','cep','endereco','numero','bairro_emp','cidade_emp','uf_emp','tel','email','logo','nome','cpf','orgao',
            'dt_nasc','endereco_adm','cep_adm','numero_adm','bairro_adm','cidade_adm','uf_adm','principal','tel_adm','email_adm','dia_venc','qtd_filial','qtd_usuarios','tp_calc_juros',
            'tp_calc_multa','ft_juros','ft_multa'
        )
    def clean(self):
        cleaned_data = super().clean()
        campos = ['ft_juros', 'ft_multa']
        for c in campos:
            try: cleaned_data[c] = parse_decimal(cleaned_data.get(c))
            except: self.add_error(c, 'Valor inválido.')
        return cleaned_data