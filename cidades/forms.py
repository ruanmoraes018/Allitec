from django import forms
from .models import Cidade

class CidadeForm(forms.ModelForm):
    nome_cidade = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Cidade
        fields = (
            'nome_cidade',
        )