from django import forms
from django.forms import inlineformset_factory
from filiais.models import Filial
from .models import Pedido, PedidoProduto
from clientes.models import Cliente

class PedidoForm(forms.ModelForm):
    cli = forms.ModelChoiceField(
        label='Cliente',
        queryset=Cliente.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )
    vinc_emp = forms.ModelChoiceField(
        label='Filial',
        queryset=Filial.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select form-select-sm border-dark-subtle',
        })
    )
    vendedor = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
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
    dt_emi = forms.DateField(
        label='Dt. Emissão',
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    dt_fat = forms.DateField(
        label='Dt. Fatura',
        input_formats=['%d/%m/%Y'],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
        })
    )
    total = forms.DecimalField(
        label="Total",
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'readonly': 'readonly'
        })
    )

    class Meta:
        model = Pedido
        fields = (
            'vinc_emp', 'cli', 'vendedor', 'obs', 'dt_emi', 'dt_fat', 'total'
        )
        widgets = {
            'dt_emi': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
            }),
            'dt_fat': forms.TextInput(attrs={
                'class': 'form-control form-control-sm border-dark-subtle',
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Formatar os valores se o form está sendo carregado com uma instância
        if self.instance and self.instance.pk:
            if self.instance.dt_emi:
                self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
            if self.instance.dt_fat:
                self.initial['dt_fat'] = self.instance.dt_fat.strftime('%d/%m/%Y')

    def clean_obs(self):
        return self.cleaned_data['obs'].upper()

PedidoProdutoFormSet = inlineformset_factory(
    Pedido,
    PedidoProduto,
    fields=["produto", "quantidade", "desc_acres"],
    extra=1,
    can_delete=True
)
