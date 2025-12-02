from django import forms
from .models import Estado

class EstadoForm(forms.ModelForm):
    nome_estado = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Estado
        fields = (
            'nome_estado',
        )