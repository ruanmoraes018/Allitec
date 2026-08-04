from django import forms
from django.contrib.auth.models import User, Permission
from filiais.models import Filial
from django.contrib.auth.forms import AuthenticationForm
from collections import OrderedDict
from django.contrib.auth import get_user_model
Usuario = get_user_model()
from django.contrib.auth.hashers import make_password
from .permissoes import (APPS_PERMISSOES, ORDEM_MAP, CATEGORIAS_PERMISSOES, GRUPOS_PERMISSOES)
from formas_pgto.models import FormaPgto
from tabelas_preco.models import TabelaPreco
from vendedores.models import Vendedor
from util.parse_decimal import parse_decimal
class SuperuserLoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuário")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)

c = 'form-control form-control-sm border-dark-subtle focus-ring focus-ring-dark'
s = 'form-select form-select-sm border-dark-subtle focus-ring focus-ring-dark'
w = forms.CheckboxInput(attrs={ 'class': 'form-check-input focus-ring focus-ring-dark', 'role': 'switch'})

class UsuarioCadastroForm(forms.ModelForm):
    gerar_senha_lib = forms.BooleanField(label="Gerar Senha de Liberação", required=False, widget=w)
    senha_liberacao = forms.CharField(label="Senha de Liberação", help_text="Para nova senha, preencha esse campo!", required=False, widget=forms.TextInput(attrs={'class': f'{c}'}))
    is_active = forms.TypedChoiceField(label='Situação', choices=(('True', 'Ativo'), ('False', 'Inativo')), coerce=lambda x: x in ['True', 'true', '1', True], widget=forms.Select(attrs={'class': f'{s}'}))
    #
    tel = forms.CharField(label="Fone", required=False, max_length=20, widget=forms.TextInput(attrs={'maxlength': '20', 'class': f'{c}'}))
    desconto_maximo = forms.CharField(label='Desconto Máximo %', widget=forms.TextInput(attrs={'class': f'{c} text-end'}))
    limite_credito = forms.CharField(label='Limite Crédito', widget=forms.TextInput(attrs={'class': f'{c} text-end'}))
    formas_pagamento = forms.ModelMultipleChoiceField(
        queryset=FormaPgto.objects.none(),required=False, widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input ms-1'}), label="Formas de Pagamento",)
    tabelas_preco = forms.ModelMultipleChoiceField(
        queryset=TabelaPreco.objects.none(),required=False, widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input ms-1'}), label="Tabelas de Preço",)
    filiais_permitidas = forms.ModelMultipleChoiceField(
        queryset=Filial.objects.none(),required=False,widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input ms-1'}),label="Filiais Permitidas",)
    vendedor = forms.ChoiceField(label="Vendedor", required=False, widget=forms.Select(attrs={"class":  f'{s}'}))
    opfilial = forms.ChoiceField(label="Acessar todas as filiais", choices=[('0', 'Não'), ('1', 'Sim')], widget=forms.Select(attrs={'class': f'{s}'}))
    opformas = forms.ChoiceField(label="Utilizar todas as formas de pagamento", choices=[('0', 'Não'), ('1', 'Sim')], widget=forms.Select(attrs={'class': f'{s}'}))
    optabelas = forms.ChoiceField(label="Utilizar todas as tabelas de preço", choices=[('0', 'Não'), ('1', 'Sim')], widget=forms.Select(attrs={'class': f'{s}'}))
    # Cards
    ver_res_orc = forms.BooleanField(label="Resumo - Orçamentos", required=False, widget=w)
    ver_res_orc_tec = forms.BooleanField(label="Resumo - Orçamento por Técnico", required=False, widget=w)
    ver_conv_orc = forms.BooleanField(label="Conversão - Orçamentos", required=False, widget=w)
    ver_ticket_medio = forms.BooleanField(label="Ticket Médio - Orçamentos", required=False, widget=w)
    ver_valor_perdido = forms.BooleanField(label="Valor Perdido - Orçamentos", required=False, widget=w)
    ver_vl_total_faturado = forms.BooleanField(label="Valor Total Faturado - Orçamentos", required=False, widget=w)
    ver_tempo_medio_faturamento = forms.BooleanField(label="Tempo Médio de Fat. - Orçamentos", required=False, widget=w)
    ver_peso_total = forms.BooleanField(label="Peso Total - Orçamentos", required=False, widget=w)
    ver_m2_total = forms.BooleanField(label="M² Total - Orçamentos", required=False, widget=w)
    ver_situacao_orcamentos = forms.BooleanField(label="Qtde. Situação - Orçamentos", required=False, widget=w)
    ver_evolucao_orcamentos = forms.BooleanField(label="Evolução - Orçamentos", required=False, widget=w)
    ver_ranking_tecnicos = forms.BooleanField(label="Ranking Técnico - Orçamentos", required=False, widget=w)
    ver_ranking_clientes = forms.BooleanField(label="Ranking Cliente - Orçamentos", required=False, widget=w)
    ver_situacao_valor_orcamentos = forms.BooleanField(label="Vl. Situação - Orçamentos", required=False, widget=w)
    ver_faturamento_diario = forms.BooleanField(label="Faturamento Diário - Orçamentos", required=False, widget=w)
    ver_top_10_produtos_qtde = forms.BooleanField(label="Top 10 Produtos (Qtde.) - Orçamentos", required=False, widget=w)
    ver_top_10_produtos_vl = forms.BooleanField(label="Top 10 Produtos (Valor) - Orçamentos", required=False, widget=w)
    ver_formas_orcamentos = forms.BooleanField(label="Formas de Pagamento - Orçamentos", required=False, widget=w)
    ver_status_orcamentos = forms.BooleanField(label="Status de Produção - Orçamentos", required=False, widget=w)
    ver_cores_orcamentos = forms.BooleanField(label="Cores - Orçamentos", required=False, widget=w)
    ver_caracteristicas_orcamentos = forms.BooleanField(label="Características - Orçamentos", required=False, widget=w)
    # Alertas
    receber_alerta_estoque = forms.BooleanField(label="Receber alerta de Est. Mínimo", required=False, widget=w)
    receber_alerta_estoque_maximo = forms.BooleanField(label="Receber alerta de Est. Máximo", required=False, widget=w)
    #
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={'class': f'{c}'}))
    permissoes = forms.ModelMultipleChoiceField(queryset=Permission.objects.filter(content_type__app_label__in=APPS_PERMISSOES), widget=forms.CheckboxSelectMultiple, required=False)
    first_name = forms.CharField(label="Nome do Usuário", widget=forms.TextInput(attrs={'class': f'{c}'}))
    email = forms.CharField(label="E-mail", widget=forms.TextInput(attrs={'class': f'{c}'}))
    password = forms.CharField(label="Senha*", help_text="Para nova senha, preencha esse campo!", widget=forms.PasswordInput(attrs={'class': f'{c}', 'type': 'password'}), required=False)
    filial_user = forms.ChoiceField(label="Filial Padrão", widget=forms.Select(attrs={'class': f'{c}'}), required=True)
    class Meta:
        model = Usuario
        fields = [
            'is_active', 'filial_user', 'first_name', 'username', 'email', 'password', 'permissoes', 'receber_alerta_estoque', 'receber_alerta_estoque_maximo',
            'gerar_senha_lib', 'senha_liberacao', 'ver_res_orc', 'ver_res_orc_tec', 'foto', 'tel', 'desconto_maximo', 'limite_credito', 'formas_pagamento',
            'ver_conv_orc', 'ver_ticket_medio', 'ver_valor_perdido', 'ver_vl_total_faturado', 'ver_tempo_medio_faturamento', 'tabelas_preco', 'filiais_permitidas',
            'ver_peso_total', 'ver_situacao_orcamentos', 'ver_evolucao_orcamentos', 'ver_ranking_tecnicos', 'ver_ranking_clientes', 'ver_situacao_valor_orcamentos',
            'ver_m2_total', 'ver_faturamento_diario', 'ver_top_10_produtos_qtde', 'ver_top_10_produtos_vl', 'ver_formas_orcamentos', 'ver_status_orcamentos',
            'ver_cores_orcamentos', 'ver_caracteristicas_orcamentos', 'vendedor', 'opfilial', 'opformas', 'optabelas',
        ]
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop("empresa", None)
        self.opfilial = kwargs.pop("opfilial", "0")
        self.opformas = kwargs.pop("opformas", "0")
        self.optabelas = kwargs.pop("optabelas", "0")
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.empresa:
            self.empresa = self.instance.empresa
        if self.empresa:
            filiais_ativas = Filial.objects.filter(vinc_emp=self.empresa, situacao="Ativa")
            self.fields["filial_user"].choices = [("", "Escolha uma opção"), *[(str(f.codigo), f.fantasia.upper()) for f in filiais_ativas]]
            vendedores = Vendedor.objects.filter(vinc_emp=self.empresa)
            self.fields["formas_pagamento"].queryset = FormaPgto.objects.filter(vinc_emp=self.empresa, situacao="Ativo")
            self.fields["tabelas_preco"].queryset = TabelaPreco.objects.filter(vinc_emp=self.empresa)
            self.fields["filiais_permitidas"].queryset = Filial.objects.filter(vinc_emp=self.empresa, situacao="Ativa")
            self.fields["vendedor"].choices = [("", "---------")] + [(str(v.codigo), v.fantasia) for v in vendedores]
            if self.instance and self.instance.pk and self.instance.filial_user: self.initial["filial_user"] = str(self.instance.filial_user.codigo)
        else:
            self.fields["filial_user"].choices = [("", "Escolha uma filial")]
        permissoes = Permission.objects.filter(content_type__app_label__in=APPS_PERMISSOES )
        permissoes_ordenadas = sorted(permissoes, key=lambda p: ORDEM_MAP.get(p.codename, 9999))
        self.fields["permissoes"].queryset = Permission.objects.filter(id__in=[p.id for p in permissoes_ordenadas])
        self.categorias_permissoes = CATEGORIAS_PERMISSOES
        grupo_permissoes = OrderedDict((grupo, []) for grupo in GRUPOS_PERMISSOES)
        for perm in permissoes_ordenadas:
            for grupo, codenames in GRUPOS_PERMISSOES.items():
                if perm.codename in codenames:
                    grupo_permissoes[grupo].append(perm)
                    break
        self.grupo_permissoes = grupo_permissoes
    # ✅ VALIDAÇÃO EXTRA À PROVA DE ERROS
    def clean_filial_user(self):
        codigo_enviado = self.cleaned_data.get('filial_user')
        if not codigo_enviado: raise forms.ValidationError("Por favor, selecione uma filial.")
        if not self.empresa: raise forms.ValidationError("Erro: empresa não definida no formulário.")
        try: filial = Filial.objects.get(codigo=codigo_enviado, vinc_emp=self.empresa)
        except Filial.DoesNotExist: raise forms.ValidationError("A filial selecionada não existe para a sua empresa.")
        if filial.situacao != 'Ativa': raise forms.ValidationError("A filial selecionada não está ativa.")
        # Retornamos o objeto Filial completo. O Django vai saber salvar no banco!
        return filial
    def save(self, commit=True):
        user = super().save(commit=False)
        senha = self.cleaned_data.get("password")
        senha_lib = self.cleaned_data.get("senha_liberacao")
        # Empresa
        if self.empresa: user.empresa = self.empresa
        # Nome
        user.first_name = self.cleaned_data.get("first_name", "").upper()
        # Filial padrão
        user.filial_user = self.cleaned_data.get("filial_user")
        # Ativo
        user.is_active = self.cleaned_data.get("is_active")
        # Senha do login
        if senha: user.set_password(senha)
        elif user.pk: user.password = Usuario.objects.get(pk=user.pk).password
        # Senha de liberação
        user.gerar_senha_lib = self.cleaned_data.get("gerar_senha_lib")
        if senha_lib: user.senha_liberacao = make_password(senha_lib)
        elif user.pk: user.senha_liberacao = Usuario.objects.get(pk=user.pk).senha_liberacao
        if commit:
            user.save()
            # Permissões
            user.user_permissions.set(self.cleaned_data.get("permissoes", []))
            # Filiais
            if self.opfilial == "1": user.filiais_permitidas.set(Filial.objects.filter(vinc_emp=self.empresa, situacao="Ativa"))
            else: user.filiais_permitidas.set(self.cleaned_data.get("filiais_permitidas", []))
            # Formas de pagamento
            if self.opformas == "1": user.formas_pagamento.set(FormaPgto.objects.filter(vinc_emp=self.empresa, situacao="Ativo"))
            else: user.formas_pagamento.set(self.cleaned_data.get("formas_pagamento", []))
            # Tabelas de preço
            if self.optabelas == "1": user.tabelas_preco.set(TabelaPreco.objects.filter(vinc_emp=self.empresa))
            else: user.tabelas_preco.set(self.cleaned_data.get("tabelas_preco", []))
        return user

    def clean(self):
        cleaned_data = super().clean()
        formas = []
        for codigo in cleaned_data["formas_pagamento"]:
            try: formas.append(FormaPgto.objects.get(codigo=codigo, vinc_emp=self.empresa))
            except FormaPgto.DoesNotExist: self.add_error("formas_pagamento", "Forma de pagamento inválida.")
        cleaned_data["formas_pagamento"] = formas
        tabelas = []
        for codigo in cleaned_data["tabelas_preco"]:
            try: tabelas.append(TabelaPreco.objects.get(codigo=codigo, vinc_emp=self.empresa))
            except TabelaPreco.DoesNotExist: self.add_error("tabelas_preco", "Forma de pagamento inválida.")
        cleaned_data["tabelas_preco"] = tabelas
        codigo = cleaned_data.get("vendedor")
        if codigo:
            try: cleaned_data["vendedor"] = Vendedor.objects.get(codigo=codigo, vinc_emp=self.empresa)
            except Vendedor.DoesNotExist: self.add_error("vendedor", "Vendedor inválido.")
        try: cleaned_data['desconto_maximo'] = parse_decimal(cleaned_data.get('desconto_maximo'))
        except: self.add_error('desconto_maximo', 'Valor inválido.')
        try: cleaned_data['limite_credito'] = parse_decimal(cleaned_data.get('limite_credito'))
        except: self.add_error('limite_credito', 'Valor inválido.')
        return cleaned_data

class UsuarioReadOnlyForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('is_active', 'first_name', 'username', 'email', 'password', 'groups')
    def __init__(self, *args, **kwargs):
        super(UsuarioReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True