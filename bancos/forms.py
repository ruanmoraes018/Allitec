from django import forms
from .models import Banco

class BancoForm(forms.ModelForm):
    nome_banco = forms.CharField(label='Nome',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    cod_banco = forms.CharField(label='Cód. Banco',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    class Meta:
        model = Banco
        fields = (
            'nome_banco', 'cod_banco'
        )