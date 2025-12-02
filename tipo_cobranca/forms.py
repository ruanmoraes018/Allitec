from django import forms
from .models import TipoCobranca

class TipoCobrancaForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = TipoCobranca
        fields = (
            'descricao',
        )