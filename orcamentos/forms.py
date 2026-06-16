from django import forms
from util.parse_decimal import parse_decimal
from .models import Orcamento, PortaAdicional, PortaOrcamento, PortaProduto
from clientes.models import Cliente
from tecnicos.models import Tecnico
from formas_pgto.models import FormaPgto
from filiais.models import Filial
from tabelas_preco.models import TabelaPreco
from django.db import models
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from fornecedores.models import Fornecedor

class OrcamentoForm(forms.ModelForm):
    cli = forms.ChoiceField(label='Cliente', widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    vinc_fil = forms.ChoiceField(label='Filial', widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    obs_cli = forms.CharField(label='Obs', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    id = forms.CharField(label='Nº', required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'disabled': 'disabled'}))
    solicitante = forms.ChoiceField(label='Técnico/Solicitante', widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    fornecedor = forms.ChoiceField(label='Fornecedor', widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    pintura = forms.ChoiceField(choices=[('Sim', 'Sim'),('Não', 'Não')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    portao_social = forms.ChoiceField(label="Portão Social", choices=[('Não', 'Não'),('Sim', 'Sim')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tp_pintura = forms.ChoiceField(label="Tipo Pintura", choices=[('Eletrostática', 'Eletrostática'),('Automotiva', 'Automotiva')], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    cor = forms.ChoiceField(
        choices = [
            ('', ''), ('Preto', 'Preto'), ('Branco', 'Branco'),('Amarelo', 'Amarelo'), ('Vermelho', 'Vermelho'),('Azul Claro', 'Azul Claro'), ('Cinza Claro', 'Cinza Claro'),
            ('Cinza Grafite', 'Cinza Grafite'), ('Cinza Chumbo', 'Cinza Chumbo'), ('Chumbo', 'Chumbo'), ('Verde', 'Verde'),('Bege', 'Bege'), ('Bege Areia', 'Bege Areia'),('Marrom', 'Marrom'), ('Marrom Café', 'Marrom Café'),
            ('Laranja', 'Laranja'), ('Azul Royal', 'Azul Royal'), ('Azul Marinho', 'Azul Marinho'), ('Azul Pepsi', 'Azul Pepsi'), ('Verde Musgo', 'Verde Musgo'),('Verde Bandeira', 'Verde Bandeira'), ('Vinho', 'Vinho'), ('Prata', 'Prata'),
        ], required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'})
    )
    obs_form_pgto = forms.CharField(label='Observações', required=False, widget=forms.Textarea(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase', 'rows': 2}))
    vl_p_s = forms.CharField(required=False, label="Valor Portão Social", widget=forms.TextInput(attrs={'placeholder': '0,00', 'readonly': 'readonly', 'class': 'form-control border-dark-subtle', 'style': 'color: darkgreen; font-weight: bold; background: honeydew;'}))
    desconto = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control border-dark-subtle', 'style': 'color: #2E8B57; font-weight: bold; background-color: #808080;', 'placeholder': '0,00', 'readonly': 'readonly'}))
    acrescimo = forms.CharField(required=False,widget=forms.TextInput(attrs={'class': 'form-control border-dark-subtle','style': 'color: #2E8B57; font-weight: bold; background-color: #808080;','placeholder': '0,00','readonly': 'readonly'}))
    dt_emi = forms.DateField(label='Dt. Emissão',input_formats=['%d/%m/%Y'],widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    dt_ent = forms.DateField(label='Dt. Entrega',required=False,input_formats=['%d/%m/%Y'],widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle'}))
    # subtotal = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle','hidden': ''}))
    # total = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle','hidden': ''}))
    formas_pgto = forms.ChoiceField(label='Formas de Pagamento', required=False, widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    tabela_preco = forms.ChoiceField(label='Tabela de Preço', widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    codigo = forms.CharField(required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    class Meta:
        model = Orcamento
        exclude = ('motivo', 'dt_fat', 'vinc_emp', 'situacao', 'status', 'status_pagamento', 'num_orcamento', 'subtotal', 'total')
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Inicializa crispy-forms (opcional, se você usa layout personalizado)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(Field('cli', wrapper_class=''), Field('fornecedor', wrapper_class=''), Field('tabela_preco', wrapper_class=''), Field('obs_cli', wrapper_class=''),)
        if not self.empresa and self.instance and self.instance.pk and getattr(self.instance, 'vinc_emp', None):
            self.empresa = self.instance.vinc_emp
        if self.empresa:
            clientes = Cliente.objects.filter(vinc_emp=self.empresa)
            tabelas = TabelaPreco.objects.filter(vinc_emp=self.empresa)
            filiais = Filial.objects.filter(vinc_emp=self.empresa)
            tecnicos = Tecnico.objects.filter(vinc_emp=self.empresa)
            fornecedores = Fornecedor.objects.filter(vinc_emp=self.empresa)
            self.fields['cli'].choices = [('', 'Escolha uma opção')] + [(str(c.codigo), c.fantasia.upper()) for c in clientes]
            self.fields['tabela_preco'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.descricao.upper()) for t in tabelas]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')] + [(str(f.codigo), f.fantasia.upper()) for f in filiais]
            self.fields['solicitante'].choices = [('', 'Escolha uma opção')] + [(str(t.codigo), t.nome.upper()) for t in tecnicos]
            self.fields['fornecedor'].choices = [('', 'Escolha uma opção')] + [(str(fn.codigo), fn.fantasia.upper()) for fn in fornecedores]
            # Define os valores iniciais em caso de Edição (Uso do código)
            if self.instance and self.instance.pk:
                if self.instance.cli: self.initial['cli'] = str(self.instance.cli.codigo)
                if self.instance.tabela_preco: self.initial['tabela_preco'] = str(self.instance.tabela_preco.codigo)
                if self.instance.vinc_fil: self.initial['vinc_fil'] = str(self.instance.vinc_fil.codigo)
                if self.instance.solicitante: self.initial['solicitante'] = str(self.instance.solicitante.codigo)
                if self.instance.fornecedor: self.initial['fornecedor'] = str(self.instance.fornecedor.codigo)
                if self.instance.dt_emi: self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
                if self.instance.dt_ent: self.initial['dt_ent'] = self.instance.dt_ent.strftime('%d/%m/%Y')
            else:
                # ✅ Se for CRIAÇÃO (Novo Registro): Pré-seleciona a filial do usuário logado
                if self.user and self.user.filial_user:
                    self.initial['vinc_fil'] = str(self.user.filial_user.codigo)
                    self.initial['cli'] = str(self.user.filial_user.cli.codigo)
                    self.initial['solicitante'] = str(self.user.filial_user.tec.codigo)
                    self.initial['tabela_preco'] = str(self.user.filial_user.tb_preco.codigo)
            # --- FORMAS DE PAGAMENTO ---
            qs_formas = FormaPgto.objects.filter(vinc_emp=self.empresa, situacao='Ativo')
            tabela = getattr(self.instance, 'tabela_preco', None)
            if tabela:
                tipo_plano = getattr(tabela, 'tipo', '').lower()
                formas_ambas = ['DINHEIRO', 'CRÉDITO', 'DÉBITO', 'PIX']
                if tipo_plano == 'a vista':
                    qs_formas = qs_formas.filter(models.Q(tipo__iexact='A vista') | models.Q(descricao__in=formas_ambas))
                else:
                    qs_formas = qs_formas.filter(models.Q(gera_parcelas=True) | models.Q(descricao__in=formas_ambas))
            self.fields['formas_pgto'].queryset = qs_formas.distinct()
        else:
            self.fields['cli'].choices = [('', 'Escolha uma opção')]
            self.fields['tabela_preco'].choices = [('', 'Escolha uma opção')]
            self.fields['vinc_fil'].choices = [('', 'Escolha uma opção')]
            self.fields['fornecedor'].choices = [('', 'Escolha uma opção')]
        # --- Inicializa campos derivados com segurança ---
        self.initial['nome_cli'] = getattr(getattr(self.instance, 'cli', None), 'fantasia', '')
        self.initial['nome_solicitante'] = getattr(getattr(self.instance, 'solicitante', None), 'nome', '')
        # --- Formata datas se houver instância existente ---
        if getattr(self.instance, 'pk', None):
            if getattr(self.instance, 'dt_emi', None): self.initial['dt_emi'] = self.instance.dt_emi.strftime('%d/%m/%Y')
            if getattr(self.instance, 'dt_ent', None): self.initial['dt_ent'] = self.instance.dt_ent.strftime('%d/%m/%Y')
    def clean_obs_cli(self):
        return self.cleaned_data['obs_cli'].upper()
    def clean_obs_form_pgto(self):
        return self.cleaned_data['obs_form_pgto'].upper()
    def clean(self):
        cleaned_data = super().clean()
        campos_select2 = {'cli': (Cliente, 'Cliente'), 'tabela_preco': (TabelaPreco, 'Tabela de Preço'), 'solicitante': (Tecnico, 'Solicitante'), 'vinc_fil': (Filial, 'Filial'), 'fornecedor': (Fornecedor, 'Fornecedor'),}
        for nome_campo, (model_classe, nome_exibicao) in campos_select2.items():
            codigo = cleaned_data.get(nome_campo)
            # Se o usuário preencheu o campo, fazemos a conversão genérica
            if codigo:
                try:
                    objeto_real = model_classe.objects.get(codigo=codigo, vinc_emp=self.empresa)
                    cleaned_data[nome_campo] = objeto_real  # Substitui o código string pelo objeto do banco
                except model_classe.DoesNotExist:
                    self.add_error(nome_campo, f"{nome_exibicao} inválido(a) para esta empresa.")
        forma = cleaned_data.get('formas_pgto')
        tabela = cleaned_data.get('tabela_preco')
        if forma and tabela:
            tipo_plano = tabela.tipo.lower()
            formas_ambas = ['DINHEIRO', 'CRÉDITO', 'DÉBITO', 'PIX']
            if tipo_plano == 'a vista' and not (forma.tipo.lower() == 'a vista' or forma.descricao.upper() in formas_ambas): raise forms.ValidationError(f"A forma {forma.descricao} não é permitida para o plano À Vista.")
            elif tipo_plano == 'a prazo' and not (forma.gera_parcelas or forma.descricao.upper() in formas_ambas): raise forms.ValidationError(f"A forma {forma.descricao} não é permitida para o plano A Prazo.")
        try: cleaned_data['desconto'] = parse_decimal(cleaned_data.get('desconto'))
        except: self.add_error('desconto', 'Valor inválido.')
        try: cleaned_data['acrescimo'] = parse_decimal(cleaned_data.get('acrescimo'))
        except: self.add_error('acrescimo', 'Valor inválido.')
        try: cleaned_data['vl_p_s'] = parse_decimal(cleaned_data.get('vl_p_s'))
        except: self.add_error('vl_p_s', 'Valor inválido.')
        return cleaned_data
class PortaOrcamentoForm(forms.ModelForm):
    rolo = forms.DecimalField(localize=False)
    largura = forms.DecimalField(localize=False)
    altura = forms.DecimalField(localize=False)
    m2 = forms.DecimalField(localize=False)
    larg_corte = forms.DecimalField(localize=False)
    alt_corte = forms.DecimalField(localize=False)
    class Meta:
        model = PortaOrcamento
        fields = '__all__'
        localized_fields = ('rolo', 'largura', 'altura', 'm2','larg_corte', 'alt_corte')

class PortaProdutoForm(forms.ModelForm):
    quantidade = forms.DecimalField(localize=False)
    class Meta:
        model = PortaProduto
        fields = ('produto', 'quantidade')
        localized_fields = ('quantidade', )

class PortaAdicionalForm(forms.ModelForm):
    quantidade = forms.DecimalField(localize=False)
    class Meta:
        model = PortaAdicional
        fields = ('produto', 'quantidade')
        localized_fields = ('quantidade', )