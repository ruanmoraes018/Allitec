from django import forms
from .models import Contrato
from empresas.models import Empresa

class ContratoForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        widget=forms.Select(
            attrs={
                'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
                'id': 'id_empresa'
            }
        ),
        label='Empresa'
    )
    dt_inicio = forms.DateField(
        label='Dt. Início',
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    situacao = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Suspenso', 'Suspenso'), ('Cancelado', 'Cancelado')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    qtd_parcelas = forms.CharField(label='Qtd. Parcelas',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'type': 'number'}))
    valor_mensalidade = forms.DecimalField(
        label='Vl. Parcela',
        max_digits=10,  # Defina conforme o modelo
        decimal_places=2,  # Defina conforme o modelo
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
            'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'
        })
    )
    obs = forms.CharField(
        label='Observações',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase',
            'rows': 2
        })
    )

    class Meta:
        model = Contrato
        exclude = ('created_at', 'updated_at', 'status')