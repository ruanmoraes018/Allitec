from django import forms
from django.forms import inlineformset_factory
from filiais.models import Filial
from .models import Pedido, PedidoProduto
from clientes.models import Cliente
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from tabelas_preco.models import TabelaPreco
from vendedores.models import Vendedor

class PedidoForm(forms.ModelForm):
    cli = forms.ModelChoiceField(label='Cliente', queryset=Cliente.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    vinc_fil = forms.ModelChoiceField(label='Filial', queryset=Filial.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tabela_preco = forms.ModelChoiceField(label='Tabela de Preços', queryset=TabelaPreco.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    vendedor = forms.ModelChoiceField(label='Vendedor', queryset=Vendedor.objects.none(), widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    obs = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    dt_emi = forms.DateField(label='Dt. Emissão', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    total = forms.DecimalField(label="Total", required=False, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))

    class Meta:
        model = Pedido
        fields = ('vinc_fil', 'cli', 'tabela_preco', 'vendedor', 'obs', 'dt_emi', 'total')
    def __init__(self, *args, empresa=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Field('cli', wrapper_class=''), Field('vinc_fil', wrapper_class=''), Field('tabela_preco', wrapper_class=''), Field('vendedor', wrapper_class=''),)
        if empresa:
            # --- CLIENTE ---
            self.fields['vinc_fil'].queryset = Filial.objects.filter(vinc_emp=empresa)
            self.fields['cli'].queryset = Cliente.objects.filter(vinc_emp=empresa)
            self.fields['tabela_preco'].queryset = TabelaPreco.objects.filter(vinc_emp=empresa)
            self.fields['vendedor'].queryset = Vendedor.objects.filter(vinc_emp=empresa)
            if not self.instance.pk and user and user.filial_user:
                self.fields['vinc_fil'].initial = user.filial_user.pk
                self.fields['cli'].initial = user.filial_user.cli.pk
                self.fields['tabela_preco'].initial = user.filial_user.tb_preco.pk
                self.fields['vendedor'].initial = user.filial_user.vendedor.pk
        # Formatar os valores se o form está sendo carregado com uma instância
        if self.instance and self.instance.pk:
            if self.instance.dt_emi:
                self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')

    def clean_obs(self):
        return self.cleaned_data['obs'].upper()

PedidoProdutoFormSet = inlineformset_factory(Pedido, PedidoProduto, fields=["produto", "quantidade", "desc_acres"], extra=1, can_delete=True)
