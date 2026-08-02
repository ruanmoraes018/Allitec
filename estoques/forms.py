from django import forms
from .models import Estoque

class EstoqueForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    class Meta:
        model = Estoque
        fields = ('descricao',)