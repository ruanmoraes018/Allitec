from django import forms
from .models import Cliente
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

class ClienteForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    pessoa = forms.ChoiceField(label="Pessoa", choices=[('Física', 'Física'), ('Jurídica', 'Jurídica')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cpf_cnpj = forms.CharField(label='CPF',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    ie = forms.CharField(label='Inscrição Estadual/RG', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    razao_social = forms.CharField(label='Razão Social',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    fantasia = forms.CharField(label='Fantasia',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    complem = forms.CharField(label='Complemento', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    bairro = forms.ModelChoiceField(
        queryset=Bairro.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_bairro'
            }
        ),
        label='Bairro'
    )
    cidade = forms.ModelChoiceField(
        queryset=Cidade.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_cidade'
            }
        ),
        label='Cidade'
    )
    uf = forms.ModelChoiceField(
        queryset=Estado.objects.all(),
        required=False,
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_uf'
            }
        ),
        label='Estado'
    )
    numero = forms.CharField(label='Nº',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail', required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    class Meta:
        model = Cliente
        fields = (
            'situacao', 'pessoa', 'cpf_cnpj', 'ie', 'razao_social', 'fantasia', 'cep', 'endereco', 'numero', 'bairro', 'complem', 'cidade', 'uf', 'tel', 'email'
        )