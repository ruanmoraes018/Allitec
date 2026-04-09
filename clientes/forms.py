from django import forms
from .models import Cliente
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from filiais.models import Filial

class ClienteForm(forms.ModelForm):
    vinc_fil = forms.ModelChoiceField(label='Filial', queryset=Filial.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle text-uppercase'}))
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    pessoa = forms.ChoiceField(label="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cpf_cnpj = forms.CharField(label='CPF', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    ie = forms.CharField(label='Inscrição Estadual/RG', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    razao_social = forms.CharField(label='Razão Social', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    complem = forms.CharField(label='Complemento', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    bairro = forms.ModelChoiceField(queryset=Bairro.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Bairro')
    cidade = forms.ModelChoiceField(queryset=Cidade.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cidade')
    uf = forms.ModelChoiceField(queryset=Estado.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    class Meta:
        model = Cliente
        fields = (
            'situacao', 'pessoa', 'cpf_cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro', 'complem', 'cidade', 'uf', 'tel', 'email', 'vinc_fil'
        )

    def __init__(self, *args, empresa=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['bairro'].queryset = Bairro.objects.filter(vinc_emp=empresa)
            self.fields['cidade'].queryset = Cidade.objects.filter(vinc_emp=empresa)
            self.fields['uf'].queryset = Estado.objects.filter(vinc_emp=empresa)
            self.fields['vinc_fil'].queryset = Filial.objects.filter(vinc_emp=empresa)
            if not self.instance.pk and user and user.filial_user:
                self.fields['vinc_fil'].initial = user.filial_user.pk