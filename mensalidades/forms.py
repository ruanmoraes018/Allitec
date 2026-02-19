from django import forms
from .models import Mensalidade
from empresas.models import Empresa

class MensalidadeForm(forms.ModelForm):
    num_mens = forms.CharField(
        label='Nr. Mensal.',
        required=False,
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'form-control bg-secondary-subtle'
        })
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
    tp_mens = forms.ChoiceField(label="Tp. Mensal.", choices=[('Boleto', 'Boleto'), ('Pix', 'Pix')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    dt_venc = forms.DateField(
        label='Dt. Venci.',
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
    vl_mens = forms.DecimalField(
        label='Vl. Mensalidade',
        max_digits=10,  # Defina conforme o modelo
        decimal_places=2,  # Defina conforme o modelo
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end',
            'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'
        })
    )
    tp_juros = forms.ChoiceField(label="Tp. Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))

    tp_multa = forms.ChoiceField(label="Tp. Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    vl_multa = forms.DecimalField(
        label='Vl. Multa',
        max_digits=10,  # Defina conforme o modelo
        decimal_places=2,  # Defina conforme o modelo
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold',
        })
    )
    vl_juros = forms.DecimalField(
        label='Vl. Juros',
        max_digits=10,  # Defina conforme o modelo
        decimal_places=2,  # Defina conforme o modelo
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold',
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
        exclude = ('created_at', 'updated_at', 'vl_pago')
        widgets = {
            'dt_venc': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.dt_venc:
                self.initial['dt_venc'] = self.instance.dt_venc.strftime('%d/%m/%Y')