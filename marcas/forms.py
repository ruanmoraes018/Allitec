from django import forms
from .models import Marca

class MarcaForm(forms.ModelForm):
    nome_marca = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Marca
        fields = (
            'nome_marca',
        )