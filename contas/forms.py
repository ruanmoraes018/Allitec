# No arquivo forms.py dentro da sua aplicação

from django import forms
from django.contrib.auth.models import User, Permission
from filiais.models import Filial
from django.contrib.auth.forms import AuthenticationForm
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from empresas.models import Empresa

Usuario = get_user_model()

class SuperuserLoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuário")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)

class EmpresaLoginForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.all(), label="Empresa", required=True)
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={'class': 'form-control text-lowercase'}))
    password = forms.CharField(label="Senha", widget=forms.PasswordInput )
    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get("empresa")
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        if not all([empresa, username, password]):
            return cleaned_data
        user = authenticate(username=username.strip().lower(), password=password, empresa_id=empresa.id)
        if user is None:
            raise forms.ValidationError("Usuário, senha ou empresa incorretos.")
        cleaned_data["user"] = user
        return cleaned_data

class UsuarioCadastroForm(forms.ModelForm):
    gerar_senha_lib = forms.BooleanField(
        label="Gerar Senha de Liberação",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'})
    )
    senha_liberacao = forms.CharField(
        label="Senha de Liberação",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    is_active = forms.TypedChoiceField(
        label='Situação',
        choices=(('True', 'Ativo'), ('False', 'Inativo')),
        coerce=lambda x: x in ['True', 'true', '1', True],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'})
    )
    alterar_senha = forms.BooleanField(
        label="Mudar senha",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'role': 'switch',
            'id': 'id_alterar_senha',
        })
    )
    username = forms.CharField(
        label="Usuário",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-lowercase'
        })
    )
    permissoes = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(
            content_type__app_label__in=[
                'entradas', 'filiais', 'usuarios', 'clientes',
                'produtos', 'orcamentos', 'tecnicos', 'tipo_cobranca', 'pedidos',
                'bairros', 'cidades', 'estados', 'grupos', 'bancos', 'unidades', 'fornecedores', 'marcas',
                'tabelas_preco',
            ]
        ),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    first_name = forms.CharField(
        label="Nome do Usuário",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-uppercase'
        })
    )
    email = forms.CharField(
        label="E-mail",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle text-lowercase'
        })
    )
    password = forms.CharField(
        label="Senha*",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-sm border-dark-subtle',
            'type': 'password'
        }),
        required=False
    )
    filial_user = forms.ModelChoiceField(
        label="Filial Padrão",
        queryset=Filial.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Usuario
        fields = [
            'is_active', 'filial_user', 'first_name', 'username', 'email',
            'password', 'permissoes', 'gerar_senha_lib', 'senha_liberacao'
        ]

    def __init__(self, *args, filial_user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Exibe a filial em caixa alta
        self.fields['filial_user'].label_from_instance = lambda obj: obj.fantasia.upper()

        # Limita filiais conforme contexto
        if self.instance.empresa:
            self.fields['filial_user'].queryset = Filial.objects.filter(
                vinc_emp=self.instance.empresa,
                situacao='Ativa'
            )
        else:
            # Caso realmente exista usuários globais
            self.fields['filial_user'].queryset = Filial.objects.filter(situacao='Ativa')


        # Preenche permissões ordenadas
        ordem_codename = [
            'view_tabelapreco', 'add_tabelapreco', 'change_tabelapreco', 'delete_tabelapreco',
            'view_formapgto', 'add_formapgto', 'change_formapgto', 'delete_formapgto',
            'view_tipocobranca', 'add_tipocobranca', 'change_tipocobranca', 'delete_tipocobranca',
            'view_entrada', 'add_entrada', 'change_entrada', 'delete_entrada', 'efetivar_entrada', 'cancelar_entrada',
            'view_bairro', 'add_bairro', 'change_bairro', 'delete_bairro',
            'view_cidade', 'add_cidade', 'change_cidade', 'delete_cidade',
            'view_estado', 'add_estado', 'change_estado', 'delete_estado',
            'view_grupo', 'add_grupo', 'change_grupo', 'delete_grupo',
            'view_unidade', 'add_unidade', 'change_unidade', 'delete_unidade',
            'view_banco', 'add_banco', 'change_banco', 'delete_banco',
            'view_filial', 'add_filial', 'change_filial', 'delete_filial',
            'view_usuario', 'add_usuario', 'change_usuario', 'delete_usuario',
            'view_produto', 'add_produto', 'change_produto', 'clonar_produto', 'delete_produto',
            'view_cliente', 'add_cliente', 'change_cliente', 'delete_cliente',
            'view_fornecedor', 'add_fornecedor', 'change_fornecedor', 'delete_fornecedor',
            'view_orcamento', 'add_orcamento', 'change_orcamento', 'clonar_orcamento',
            'delete_orcamento', 'atribuir_desconto', 'atribuir_acrescimo',
            'faturar_orcamento', 'cancelar_orcamento',
            'view_tecnico', 'add_tecnico', 'change_tecnico', 'delete_tecnico',
            'view_marca', 'add_marca', 'change_marca', 'delete_marca',
            'view_regraproduto', 'add_regraproduto', 'change_regraproduto', 'delete_regraproduto'
            'view_pedido', 'add_pedido', 'change_pedido', 'delete_pedido', 'faturar_pedido', 'cancelar_pedido', 'atribuir_desconto_ped', 'atribuir_acrescimo_ped',
        ]

        permissoes = Permission.objects.filter(
            content_type__app_label__in=[
                'formas_pgto', 'tipo_cobranca', 'entradas', 'bairros', 'cidades', 'estados',
                'grupos', 'bancos', 'unidades', 'filiais', 'usuarios', 'tabelas_preco',
                'clientes', 'fornecedores', 'produtos', 'orcamentos', 'tecnicos', 'pedidos', 'marcas', 'regras_produto',
            ]
        )
        permissoes_ordenadas = sorted(
            permissoes,
            key=lambda p: ordem_codename.index(p.codename) if p.codename in ordem_codename else len(ordem_codename)
        )

        self.fields['permissoes'].queryset = Permission.objects.filter(
            id__in=[p.id for p in permissoes_ordenadas]
        )

        # Agrupamento para usar no template
        self.categorias_permissoes = OrderedDict({
            'Complementos': ['Bairros', 'Bancos', 'Cidades', 'Estados', 'Grupos', 'Marcas', 'Unidades', 'Tabelas de Preço', 'Tipos de Cobrança', 'Formas de Pagamento', 'Regras de Produto'],
            'Cadastros': ['Clientes', 'Filiais', 'Fornecedores', 'Produtos', 'Técnicos', 'Usuários'],
            'Estoque': ['Entradas de NF/Pedidos'],
            'Faturamento': ['Pedidos', 'Orçamentos'],
        })

        grupo_permissoes = OrderedDict({
            'Regras de Produto': [],
            'Formas de Pagamento': [],
            'Tipos de Cobrança': [],
            'Tabelas de Preço': [],
            'Entradas de NF/Pedidos': [],
            'Bairros': [],
            'Cidades': [],
            'Estados': [],
            'Grupos': [],
            'Bancos': [],
            'Marcas': [],
            'Unidades': [],
            'Filiais': [],
            'Fornecedores': [],
            'Usuários': [],
            'Produtos': [],
            'Clientes': [],
            'Pedidos': [],
            'Orçamentos': [],
            'Técnicos': [],
        })
        # Permissões por App
        entradas_perms = [
            'view_entrada', 'add_entrada', 'change_entrada', 'delete_entrada',
            'efetivar_entrada', 'cancelar_entrada'
        ]

        produtos_perms = [
            'view_produto', 'add_produto', 'change_produto', 'delete_produto',
            'clonar_produto'
        ]

        formas_perms = [
            'view_formapgto', 'add_formapgto', 'change_formapgto', 'delete_formapgto'
        ]

        tabelas_perms = [
            'view_tabelapreco', 'add_tabelapreco', 'change_tabelapreco', 'delete_tabelapreco'
        ]

        marcas_perms = [
            'view_marca', 'add_marca', 'change_marca', 'delete_marca'
        ]

        regras_perms = [
            'view_regraproduto', 'add_regraproduto', 'change_regraproduto', 'delete_regraproduto'
        ]

        orcamentos_perms = [
            'view_orcamento', 'add_orcamento', 'change_orcamento', 'clonar_orcamento',
            'delete_orcamento', 'atribuir_desconto', 'atribuir_acrescimo',
            'faturar_orcamento', 'cancelar_orcamento',
        ]

        pedidos_perms = [
            'view_pedido', 'add_pedido', 'change_pedido', 'clonar_pedido',
            'delete_pedido', 'atribuir_desconto_ped', 'atribuir_acrescimo_ped',
            'faturar_pedido', 'cancelar_pedido',
        ]

        for perm in permissoes_ordenadas:
            if 'bairro' in perm.codename:
                grupo_permissoes['Bairros'].append(perm)
            elif perm.codename in pedidos_perms:
                grupo_permissoes['Pedidos'].append(perm)
            elif perm.codename in formas_perms:
                grupo_permissoes['Formas de Pagamento'].append(perm)
            elif perm.codename in tabelas_perms:
                grupo_permissoes['Tabelas de Preço'].append(perm)
            elif perm.codename in marcas_perms:
                grupo_permissoes['Marcas'].append(perm)
            elif 'tipocobranca' in perm.codename:
                grupo_permissoes['Tipos de Cobrança'].append(perm)
            elif perm.codename in entradas_perms:
                grupo_permissoes['Entradas de NF/Pedidos'].append(perm)
            elif perm.codename in regras_perms:
                grupo_permissoes['Regras de Produto'].append(perm)
            elif 'cidade' in perm.codename:
                grupo_permissoes['Cidades'].append(perm)
            elif 'estado' in perm.codename:
                grupo_permissoes['Estados'].append(perm)
            elif 'grupo' in perm.codename:
                grupo_permissoes['Grupos'].append(perm)
            elif 'banco' in perm.codename:
                grupo_permissoes['Bancos'].append(perm)
            elif 'unidade' in perm.codename:
                grupo_permissoes['Unidades'].append(perm)
            elif 'filial' in perm.codename:
                grupo_permissoes['Filiais'].append(perm)
            elif 'fornecedor' in perm.codename:
                grupo_permissoes['Fornecedores'].append(perm)
            elif 'usuario' in perm.codename:
                grupo_permissoes['Usuários'].append(perm)
            elif perm.codename in produtos_perms:
                grupo_permissoes['Produtos'].append(perm)
            elif 'cliente' in perm.codename:
                grupo_permissoes['Clientes'].append(perm)
            elif perm.codename in orcamentos_perms:
                grupo_permissoes['Orçamentos'].append(perm)
            elif 'tecnico' in perm.codename:
                grupo_permissoes['Técnicos'].append(perm)

        self.grupo_permissoes = grupo_permissoes

    def save(self, commit=True):
        user = super().save(commit=False)
        alterar = self.cleaned_data.get('alterar_senha')
        nova_senha = self.cleaned_data.get('password')
        if alterar and nova_senha:
            user.set_password(nova_senha)
        elif not alterar and user.pk:
            old_password = Usuario.objects.get(pk=user.pk).password
            user.password = old_password
        user.filial_user = self.cleaned_data.get('filial_user')
        # campos extras
        user.gerar_senha_lib = self.cleaned_data['gerar_senha_lib']
        user.senha_liberacao = self.cleaned_data['senha_liberacao']
        user.is_active = self.cleaned_data['is_active'] in [True, 'True', 'true', 1, '1']
        user.first_name = self.cleaned_data.get('first_name', '').upper()
        if commit:
            user.save()
            user.user_permissions.set(self.cleaned_data['permissoes'])

        return user


class UsuarioReadOnlyForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'is_active', 'first_name', 'username', 'email', 'password', 'groups', 'user_permissions'
        )


    def __init__(self, *args, **kwargs):
        super(UsuarioReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True