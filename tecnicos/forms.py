from django import forms
from .models import Tecnico
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado

class TecnicoForm(forms.ModelForm):
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    nome = forms.CharField(label='Nome', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    endereco = forms.CharField(label='Endereço', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cep = forms.CharField(label='CEP', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    bairro = forms.ModelChoiceField(queryset=Bairro.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Bairro')
    cidade = forms.ModelChoiceField(queryset=Cidade.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cidade')
    uf = forms.ModelChoiceField(queryset=Estado.objects.none(), required=False, widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Estado')
    numero = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tel = forms.CharField(label="Fone", max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': 'form-control form-control-sm border-dark-subtle'}))
    email = forms.CharField(label='E-mail', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    class Meta:
        model = Tecnico
        fields = (
            'situacao', 'nome', 'cep', 'endereco', 'numero', 'bairro', 'cidade', 'uf', 'tel', 'email'
        )
    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['bairro'].queryset = Bairro.objects.filter(vinc_emp=empresa)
            self.fields['cidade'].queryset = Cidade.objects.filter(vinc_emp=empresa)
            self.fields['uf'].queryset = Estado.objects.filter(vinc_emp=empresa)