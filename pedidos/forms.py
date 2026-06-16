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
    cli = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Cliente')
    vinc_fil = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Filial')
    tabela_preco = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Tabela de Preço')
    vendedor = forms.ChoiceField(widget=forms.Select(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}), label='Vendedor')
    obs = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    dt_emi = forms.DateField(label='Dt. Emissão', input_formats=['%d/%m/%Y'], widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    total = forms.DecimalField(label="Total", required=False, widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'readonly': 'readonly'}))

    class Meta:
        model = Pedido
        fields = ('vinc_fil', 'cli', 'tabela_preco', 'vendedor', 'obs', 'dt_emi', 'total')
    def __init__(self, *args, **kwargs):
        # Captura e remove a empresa dos kwargs de forma segura
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Field('cli', wrapper_class=''), Field('vinc_fil', wrapper_class=''), Field('tabela_preco', wrapper_class=''), Field('vendedor', wrapper_class=''),)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            clientes = Cliente.objects.filter(vinc_emp=self.empresa)
            tabelas = TabelaPreco.objects.filter(vinc_emp=self.empresa)
            vendedores = Vendedor.objects.filter(vinc_emp=self.empresa)
            filiais = Filial.objects.filter(vinc_emp=self.empresa)
            self.fields['cli'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.fantasia.upper()) for c in clientes]
            self.fields['tabela_preco'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.descricao.upper()) for t in tabelas]
            self.fields['vendedor'].choices = [('', 'Escolha uma opção')] + [(str(v.codigo), v.fantasia.upper()) for v in vendedores]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')] + [(str(f.codigo), f.fantasia.upper()) for f in filiais]
            # Define os valores iniciais em caso de Edição (Uso do código)
            if self.instance and self.instance.pk:
                if self.instance.cli: self.initial['cli'] = str(self.instance.cli.codigo)
                if self.instance.tabela_preco: self.initial['tabela_preco'] = str(self.instance.tabela_preco.codigo)
                if self.instance.vendedor: self.initial['vendedor'] = str(self.instance.vendedor.codigo)
                if self.instance.vinc_fil: self.initial['vinc_fil'] = str(self.instance.vinc_fil.codigo)
                if self.instance.dt_emi: self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['vinc_fil'] = str(self.user.filial_user.codigo)
                    self.initial['cli'] = str(self.user.filial_user.cli.codigo)
                    self.initial['vendedor'] = str(self.user.filial_user.vendedor.codigo)
                    self.initial['tabela_preco'] = str(self.user.filial_user.tb_preco.codigo)
        else:
            self.fields['cli'].choices = [('', 'Escolha uma opção')]
            self.fields['tabela_preco'].choices = [('', 'Escolha uma opção')]
            self.fields['vendedor'].choices = [('', 'Escolha uma opção')]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')]
    def clean_obs(self):
        return self.cleaned_data['obs'].upper()
    def clean(self):
        cleaned_data = super().clean()
        # Mapeamento genérico: 'nome_no_form': (ClasseDoModel, 'Nome Amigável para o Erro')
        campos_select2 = {'cli': (Cliente, 'Cliente'), 'tabela_preco': (TabelaPreco, 'Tabela de Preço'), 'vendedor': (Vendedor, 'Vendedor'), 'vinc_fil': (Filial, 'Filial'),}
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
PedidoProdutoFormSet = inlineformset_factory(Pedido, PedidoProduto, fields=["produto", "quantidade", "desc_acres"], extra=1, can_delete=True)