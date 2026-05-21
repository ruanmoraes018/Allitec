from django import forms
from django.forms import inlineformset_factory
from filiais.models import Filial
from util.parse_decimal import parse_decimal
from .models import Entrada, EntradaProduto
from fornecedores.models import Fornecedor

class EntradaForm(forms.ModelForm):
    fornecedor = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Fornecedor')
    vinc_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    obs = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    numeracao = forms.CharField(label='Nº', widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    tp_frete = forms.ChoiceField(label="Frete", choices=[('CIF', 'CIF'), ('FOB', 'FOB')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tipo = forms.ChoiceField(choices=[('Pedido', 'Pedido'), ('Nota Fiscal', 'Nota Fiscal')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    modelo = forms.CharField(label='Modelo', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    serie = forms.CharField(label='Série', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    nat_op = forms.CharField(label='Natureza de Operação', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    chave_acesso = forms.CharField(label='Chave de Acesso', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))
    motivo = forms.CharField(label='Motivo', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dt_emi = forms.DateField(label='Dt Emissão.', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dt_ent = forms.DateField(label='Dt Entrega', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    frete = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'hidden': ''}))
    total = forms.DecimalField(label="Total", required=False, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))

    class Meta:
        model = Entrada
        exclude = ('vinc_emp', 'situacao', 'motivo')

    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            fornecedores = Fornecedor.objects.filter(vinc_emp=self.empresa)
            filiais = Filial.objects.filter(vinc_emp=self.empresa)
            self.fields['fornecedor'].choices = [('', 'Escolha uma opção')] + [(str(fn.codigo), fn.fantasia.upper()) for fn in fornecedores]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')] + [(str(f.codigo), f.fantasia.upper()) for f in filiais]
            if self.instance and self.instance.pk:
                if self.instance.fornecedor: self.initial['fornecedor'] = str(self.instance.fornecedor.codigo)
                if self.instance.vinc_fil: self.initial['vinc_fil'] = str(self.instance.vinc_fil.codigo)
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['vinc_fil'] = str(self.user.filial_user.codigo)
        else:
            self.fields['fornecedor'].choices = [('', 'Escolha uma opção')]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')]
    def clean_obs(self):
        return self.cleaned_data['obs'].upper()
    def clean(self):
        cleaned_data = super().clean()
        try: cleaned_data['frete'] = parse_decimal(cleaned_data.get('frete'))
        except: self.add_error('frete', 'Valor inválido.')
        campos_select2 = {'fornecedor': (Fornecedor, 'Fornecedor'), 'vinc_fil': (Filial, 'Filial'),}
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo, fazemos a conversão genérica
            if codigo:
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui o código string pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
        return cleaned_data

EntradaProdutoFormSet = inlineformset_factory(Entrada, EntradaProduto, fields=["produto", "quantidade", "preco_unitario", "desconto"], extra=1, can_delete=True)