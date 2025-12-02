from django import forms
from .models import TabelaPreco

class TabelaPrecoForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    margem = forms.DecimalField(
        label="Margem (%)",
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle'
        })
    )
    class Meta:
        model = TabelaPreco
        fields = (
            'descricao', 'margem'
        )