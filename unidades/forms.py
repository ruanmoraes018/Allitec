from django import forms
from .models import Unidade

class UnidadeForm(forms.ModelForm):
    nome_unidade = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Unidade
        fields = (
            'nome_unidade',
        )