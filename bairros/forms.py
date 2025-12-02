from django import forms
from .models import Bairro

class BairroForm(forms.ModelForm):
    nome_bairro = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Bairro
        fields = (
            'nome_bairro',
        )