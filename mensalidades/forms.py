from django import forms
from .models import Mensalidade
from empresas.models import Empresa

class MensalidadeForm(forms.ModelForm):
    num_mens = forms.CharField(
        label='Nr. Mensal.',
        required=False,
        widget=forms.TextInput(attrs={'disabled': 'disabled'})
    )
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
    situacao = forms.ChoiceField(label="Situação", choices=[('Aberta', 'Aberta'), ('Baixada', 'Baixada')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_mens = forms.ChoiceField(label="Tipo Mensalidade", choices=[('Boleto', 'Boleto'), ('Pix', 'Pix')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    dt_venc = forms.DateField(
        label='Dt. Vencimento',
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    dt_pag = forms.DateField(
        label='Dt. Pagamento',
        required=False,
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    qtd_mens = forms.CharField(label='Qtd. Mensal.',
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'type': 'number'}))
    vl_mens = forms.DecimalField(
        label='Valor',
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
        model = Mensalidade
        exclude = ('created_at', 'updated_at')