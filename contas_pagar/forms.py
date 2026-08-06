from django import forms
from util.parse_decimal import parse_decimal
from .models import ContaPagar
from filiais.models import Filial
from fornecedores.models import Fornecedor
from tipo_cobranca.models import TipoCobranca

class ContaPagarForm(forms.ModelForm):
    num_conta = forms.CharField(label='Nº Conta', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    filial = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    fornecedor = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Fornecedor')
    tp_cobranca = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Tipo de Cobrança')
    data_vencimento = forms.DateField(label='Dt. Vencimento', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    valor = forms.CharField(label='Vl. Conta', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end', 'placeholder': '0,00', 'style': 'background-color: #2E8B57; color: white; font-weight: bold;'}))
    tp_juros = forms.ChoiceField(label="Tp. Juros", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_multa = forms.ChoiceField(label="Tp. Multa", choices=[('Percentual', 'Percentual'), ('Valor', 'Valor')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    multa = forms.CharField(label='Vl. Multa', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    juros = forms.CharField(label='Vl. Juros', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase text-end fw-bold'}))
    observacao = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    status = forms.ChoiceField(label="Situação", choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    class Meta:
        model = ContaPagar
        exclude = ('tipo', 'empresa', 'situacao', 'valor_pago', 'orcamento', 'pedido', 'desconto', 'data_emissao', 'motivo')
        widgets = {'data_vencimento': forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle',}),}
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'empresa', None):
            self.empresa = self.instance.empresa
        if self.empresa:
            fornecedores = Fornecedor.objects.filter(vinc_emp=self.empresa)
            filiais = Filial.objects.filter(vinc_emp=self.empresa)
            tipos_cobrancas = TipoCobranca.objects.filter(vinc_emp=self.empresa)
            self.fields['fornecedor'].choices = [('', 'Escolha uma opção')] + [(str(fn.codigo), fn.fantasia.upper()) for fn in fornecedores]
            self.fields['filial'].choices = [('', 'Escolha uma opção')] + [(str(f.codigo), f.fantasia.upper()) for f in filiais]
            self.fields['tp_cobranca'].choices = [('', 'Escolha uma opção')] + [(str(tc.codigo), tc.descricao.upper()) for tc in tipos_cobrancas]
            if self.instance and self.instance.pk:
                if self.instance.fornecedor: self.initial['fornecedor'] = str(self.instance.fornecedor.codigo)
                if self.instance.filial: self.initial['filial'] = str(self.instance.filial.codigo)
                if self.instance.tp_cobranca: self.initial['tp_cobranca'] = str(self.instance.tp_cobranca.codigo)
                if self.instance.data_vencimento: self.initial['data_vencimento'] = self.instance.data_vencimento.strftime('%d/%m/%Y')
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['filial'] = str(self.user.filial_user.codigo)
                    self.initial['tp_cobranca'] = str(self.user.filial_user.tp_cobranca)
        else:
            self.fields['fornecedor'].choices = [('', 'Escolha uma opção')]
            self.fields['filial'].choices = [('', 'Escolha uma opção')]
            self.fields['tp_cobranca'].choices = [('', 'Escolha uma opção')]
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['frete'] = parse_decimal(cleaned_data.get('frete'))
        except: self.add_error('frete', 'Valor inválido.')
        campos_select2 = {'fornecedor': (Fornecedor, 'Fornecedor'), 'filial': (Filial, 'Filial'), 'tp_cobranca': (TipoCobranca, 'Tipo de Cobrança')}
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo, fazemos a conversão genérica
            if codigo:
                try:
                    # Descobre se o modelo usa 'vinc_emp' ou 'empresa'
                    campos_modelo = {f.name for f in model_classe._meta.fields}
                    filtros = {'codigo': codigo}
                    if 'vinc_emp' in campos_modelo:
                        filtros['vinc_emp'] = self.empresa
                    elif 'empresa' in campos_modelo:
                        filtros['empresa'] = self.empresa
                    objeto_real = model_classe.objects.get(**filtros)
                    cleaned_data[nome_campo] = objeto_real
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
            else:
                # Campo vazio -> salva NULL
                cleaned_data[nome_campo] = None
        try: cleaned_data['valor'] = parse_decimal(cleaned_data.get('valor'))
        except: self.add_error('valor', 'Valor inválido.')
        try: cleaned_data['multa'] = parse_decimal(cleaned_data.get('multa'))
        except: self.add_error('multa', 'Valor inválido.')
        try: cleaned_data['juros'] = parse_decimal(cleaned_data.get('juros'))
        except: self.add_error('juros', 'Valor inválido.')
        return cleaned_data