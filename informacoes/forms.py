from django import forms
from .models import Informacoes

class InformacoesForm(forms.ModelForm):
    descricao = forms.CharField(label='Descrição', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    conteudo = forms.CharField(label='Conteúdo', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'rows': 3}))
    class Meta:
        model = Informacoes
        fields = ('descricao', 'conteudo')