from django import forms

from util.parse_decimal import parse_decimal
from .models import ContaReceber
from filiais.models import Filial
from clientes.models import Cliente

class ContaReceberForm(forms.ModelForm):
    num_conta = forms.CharField(label='Nº Conta', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    vinc_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    cliente = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cliente')
    data_vencimento = forms.DateField(label='Dt. Vencimento', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    valor = forms.CharField(label='Vl. Conta', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end', 'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'}))
    tp_juros = forms.ChoiceField(label="Tp. Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_multa = forms.ChoiceField(label="Tp. Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    multa = forms.CharField(label='Vl. Multa', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    juros = forms.CharField(label='Vl. Juros', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    observacao = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    class Meta:
        model = ContaReceber
        exclude = ('tipo', 'vinc_emp', 'situacao', 'valor_pago', 'orcamento', 'pedido', 'forma_pgto', 'desconto', 'data_emissao', 'motivo')
        widgets = {'data_vencimento': forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle',}),}
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            clientes = Cliente.objects.filter(vinc_emp=self.empresa)
            filiais = Filial.objects.filter(vinc_emp=self.empresa)
            self.fields['cliente'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.fantasia.upper()) for c in clientes]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')] + [(str(f.codigo), f.fantasia.upper()) for f in filiais]
            if self.instance and self.instance.pk:
                if self.instance.cliente: self.initial['cliente'] = str(self.instance.cliente.codigo)
                if self.instance.vinc_fil: self.initial['vinc_fil'] = str(self.instance.vinc_fil.codigo)
                if self.instance.data_vencimento: self.initial['data_vencimento'] = self.instance.data_vencimento.strftime('%d/%m/%Y')
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['vinc_fil'] = str(self.user.filial_user.codigo)
        else:
            self.fields['cliente'].choices = [('', 'Escolha uma opção')]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')]
    def clean(self):
        cleaned_data = super().clean()
        campos_select2 = {'cliente': (Cliente, 'Cliente'), 'vinc_fil': (Filial, 'Filial'),}
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo, fazemos a conversão genérica
            if codigo:
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui o código string pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
        try: cleaned_data['valor'] = parse_decimal(cleaned_data.get('valor'))
        except: self.add_error('valor', 'Valor inválido.')
        try: cleaned_data['multa'] = parse_decimal(cleaned_data.get('multa'))
        except: self.add_error('multa', 'Valor inválido.')
        try: cleaned_data['juros'] = parse_decimal(cleaned_data.get('juros'))
        except: self.add_error('juros', 'Valor inválido.')
        return cleaned_data