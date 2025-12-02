from django import forms
from .models import Grupo

class GrupoForm(forms.ModelForm):
    nome_grupo = forms.CharField(label='Descrição',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Grupo
        fields = (
            'nome_grupo',
        )