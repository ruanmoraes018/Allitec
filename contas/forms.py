from django import forms
from django.contrib.auth.models import User, Permission
from filiais.models import Filial
from django.contrib.auth.forms import AuthenticationForm
from collections import OrderedDict
from django.contrib.auth import get_user_model
Usuario = get_user_model()
class SuperuserLoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuário")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)
class UsuarioCadastroForm(forms.ModelForm):
    gerar_senha_lib = forms.BooleanField(label="Gerar Senha de Liberação", required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}))
    senha_liberacao = forms.CharField(label="Senha de Liberação", help_text="Para nova senha, preencha esse campo!", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    is_active = forms.TypedChoiceField(label='Situação', choices=(('True', 'Ativo'), ('False', 'Inativo')), coerce=lambda x: x in ['True', 'true', '1', True], widget=forms.Select(attrs={'class': 'form-select form-select-sm border-dark-subtle'}))
    ver_res_orc = forms.BooleanField(label="Ver Resumo Orçamentos", required=False, widget=forms.CheckboxInput(attrs={ 'class': 'form-check-input', 'role': 'switch'}))
    ver_res_orc_tec = forms.BooleanField(label="Ver Resumo Orçamento por Técnico", required=False, widget=forms.CheckboxInput(attrs={ 'class': 'form-check-input', 'role': 'switch'}))
    username = forms.CharField(label="Usuário", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    permissoes = forms.ModelMultipleChoiceField(queryset=Permission.objects.filter(content_type__app_label__in=['entradas', 'filiais', 'usuarios', 'clientes', 'produtos', 'orcamentos', 'tecnicos', 'tipo_cobranca', 'pedidos',
        'lancpdvs', 'pdvs', 'bairros', 'cidades', 'estados', 'grupos', 'bancos', 'unidades', 'fornecedores', 'marcas', 'tabelas_preco', 'contas_receber' ]), widget=forms.CheckboxSelectMultiple, required=False)
    first_name = forms.CharField(label="Nome do Usuário", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-uppercase'}))
    email = forms.CharField(label="E-mail", widget=forms.TextInput(attrs={'class': 'form-control form-control-sm border-dark-subtle text-lowercase'}))
    password = forms.CharField(label="Senha*", help_text="Para nova senha, preencha esse campo!", widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm border-dark-subtle', 'type': 'password'}), required=False)
    filial_user = forms.ChoiceField(
        label="Filial Padrão",
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    class Meta:
        model = Usuario
        fields = ['is_active', 'filial_user', 'first_name', 'username', 'email', 'password', 'permissoes', 'gerar_senha_lib', 'senha_liberacao', 'ver_res_orc', 'ver_res_orc_tec']
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if not self.empresa and self.instance and self.instance.pk and self.instance.empresa:
            self.empresa = self.instance.empresa
        # 2. Alimentamos as choices com o (codigo, fantasia) em vez de (id, fantasia)
        if self.empresa:
            filiais_ativas = Filial.objects.filter(vinc_emp=self.empresa, situacao='Ativa')
            self.fields['filial_user'].choices = [('', 'Escolha uma opção')] + [
                (str(f.codigo), f.fantasia.upper()) for f in filiais_ativas
            ]
            # Se for edição, define o valor inicial usando o 'codigo'
            if self.instance and self.instance.pk and self.instance.filial_user:
                self.initial['filial_user'] = str(self.instance.filial_user.codigo)
        else:
            self.fields['filial_user'].choices = [('', 'Escolha uma filial')]
        ordem_codename = [
            'view_caixa', 'add_caixa', 'change_caixa', 'delete_caixa',
            'view_pdv', 'add_pdv', 'change_pdv', 'delete_pdv',
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
            'view_produto', 'add_produto', 'change_produto', 'clonar_produto', 'delete_produto', 'relatorio_vendas_produto',
            'view_cliente', 'add_cliente', 'change_cliente', 'delete_cliente',
            'view_fornecedor', 'add_fornecedor', 'change_fornecedor', 'delete_fornecedor',
            'view_vendedor', 'add_vendedor', 'change_vendedor', 'delete_vendedor',
            'view_orcamento', 'add_orcamento', 'change_orcamento', 'clonar_orcamento', 'delete_orcamento', 'atribuir_desconto', 'atribuir_acrescimo', 'faturar_orcamento', 'cancelar_orcamento', 'alterar_dt_venc_orc', 'alterar_dt_fat_orc', 'vender_sem_estoque_orc',
            'view_tecnico', 'add_tecnico', 'change_tecnico', 'delete_tecnico',
            'view_marca', 'add_marca', 'change_marca', 'delete_marca',
            'view_regraproduto', 'add_regraproduto', 'change_regraproduto', 'delete_regraproduto',
            'view_pedido', 'add_pedido', 'change_pedido', 'delete_pedido', 'faturar_pedido', 'cancelar_pedido', 'atribuir_desconto_ped', 'atribuir_acrescimo_ped', 'vender_sem_estoque_ped',
            'alt_vl_ped', 'alterar_data_faturamento', 'relatorio_pedidos',
            'view_contareceber', 'add_contareceber', 'change_contareceber', 'delete_contareceber', 'atribuir_desconto_cr', 'baixar_cr', 'estornar_cr',
        ]
        permissoes = Permission.objects.filter(content_type__app_label__in=['formas_pgto', 'tipo_cobranca', 'entradas', 'bairros', 'cidades', 'estados', 'grupos', 'bancos', 'unidades', 'filiais', 'usuarios', 'tabelas_preco',
            'lancpdvs', 'pdvs', 'clientes', 'fornecedores', 'vendedores', 'produtos', 'orcamentos', 'tecnicos', 'pedidos', 'marcas', 'regras_produto', 'contas_receber'])
        permissoes_ordenadas = sorted(permissoes, key=lambda p: ordem_codename.index(p.codename) if p.codename in ordem_codename else len(ordem_codename))
        self.fields['permissoes'].queryset = Permission.objects.filter(id__in=[p.id for p in permissoes_ordenadas])
        self.categorias_permissoes = OrderedDict({'Complementos': ['Bairros', 'Bancos', 'Cidades', 'Estados', 'Grupos', 'Marcas', 'Unidades', 'Tabelas de Preço', 'Tipos de Cobrança', 'Formas de Pagamento', 'Regras de Produto'],
            'Cadastros': ['Clientes', 'Filiais', 'Fornecedores', 'Produtos', 'Técnicos', 'Usuários', 'Vendedores', 'PDVs'], 'Estoque': ['Entradas de NF/Pedidos'], 'Faturamento': ['Pedidos', 'Caixas', 'Orçamentos'], 'Financeiro': ['Contas à Receber',],})
        grupo_permissoes = OrderedDict({'Regras de Produto': [], 'Formas de Pagamento': [], 'Tipos de Cobrança': [], 'Tabelas de Preço': [], 'Entradas de NF/Pedidos': [], 'Contas à Receber': [], 'Bairros': [], 'Cidades': [],
            'PDVs': [], 'Estados': [], 'Grupos': [], 'Bancos': [], 'Marcas': [], 'Unidades': [], 'Filiais': [], 'Fornecedores': [], 'Usuários': [], 'Produtos': [], 'Clientes': [], 'Pedidos': [], 'Orçamentos': [], 'Caixas': [], 'Técnicos': [], 'Vendedores': [],})
        # Permissões por App
        pdvs_perms = ['view_pdv', 'add_pdv', 'change_pdv', 'delete_pdv']
        caixa_perms = ['view_caixa', 'add_caixa', 'change_caixa', 'delete_caixa']
        entradas_perms = ['view_entrada', 'add_entrada', 'change_entrada', 'delete_entrada', 'efetivar_entrada', 'cancelar_entrada']
        fornecedores_perms = ['view_fornecedor', 'add_fornecedor', 'change_fornecedor', 'delete_fornecedor']
        vendedores_perms = ['view_vendedor', 'add_vendedor', 'change_vendedor', 'delete_vendedor']
        produtos_perms = ['view_produto', 'add_produto', 'change_produto', 'delete_produto', 'clonar_produto', 'relatorio_vendas_produto']
        formas_perms = ['view_formapgto', 'add_formapgto', 'change_formapgto', 'delete_formapgto']
        tabelas_perms = ['view_tabelapreco', 'add_tabelapreco', 'change_tabelapreco', 'delete_tabelapreco']
        marcas_perms = ['view_marca', 'add_marca', 'change_marca', 'delete_marca']
        regras_perms = ['view_regraproduto', 'add_regraproduto', 'change_regraproduto', 'delete_regraproduto']
        orcamentos_perms = ['view_orcamento', 'add_orcamento', 'change_orcamento', 'clonar_orcamento', 'delete_orcamento', 'atribuir_desconto', 'atribuir_acrescimo', 'faturar_orcamento', 'cancelar_orcamento', 'alterar_dt_venc_orc', 'alterar_dt_fat_orc', 'vender_sem_estoque_orc']
        pedidos_perms = ['view_pedido', 'add_pedido', 'change_pedido', 'clonar_pedido', 'delete_pedido', 'atribuir_desconto_ped', 'atribuir_acrescimo_ped', 'faturar_pedido',
                         'cancelar_pedido', 'vender_sem_estoque_ped', 'alt_vl_ped', 'alterar_data_faturamento', 'relatorio_pedidos']
        cr_perms = ['view_contareceber', 'add_contareceber', 'change_contareceber', 'delete_contareceber', 'atribuir_desconto_cr', 'baixar_cr', 'estornar_cr',]
        for perm in permissoes_ordenadas:
            if 'bairro' in perm.codename: grupo_permissoes['Bairros'].append(perm)
            elif perm.codename in caixa_perms: grupo_permissoes['Caixas'].append(perm)
            elif perm.codename in pdvs_perms: grupo_permissoes['PDVs'].append(perm)
            elif perm.codename in pedidos_perms: grupo_permissoes['Pedidos'].append(perm)
            elif perm.codename in formas_perms: grupo_permissoes['Formas de Pagamento'].append(perm)
            elif perm.codename in tabelas_perms: grupo_permissoes['Tabelas de Preço'].append(perm)
            elif perm.codename in marcas_perms: grupo_permissoes['Marcas'].append(perm)
            elif 'tipocobranca' in perm.codename: grupo_permissoes['Tipos de Cobrança'].append(perm)
            elif perm.codename in entradas_perms: grupo_permissoes['Entradas de NF/Pedidos'].append(perm)
            elif perm.codename in regras_perms: grupo_permissoes['Regras de Produto'].append(perm)
            elif perm.codename in cr_perms: grupo_permissoes['Contas à Receber'].append(perm)
            elif 'cidade' in perm.codename: grupo_permissoes['Cidades'].append(perm)
            elif 'estado' in perm.codename: grupo_permissoes['Estados'].append(perm)
            elif 'grupo' in perm.codename: grupo_permissoes['Grupos'].append(perm)
            elif 'banco' in perm.codename: grupo_permissoes['Bancos'].append(perm)
            elif 'unidade' in perm.codename: grupo_permissoes['Unidades'].append(perm)
            elif 'filial' in perm.codename: grupo_permissoes['Filiais'].append(perm)
            elif perm.codename in fornecedores_perms: grupo_permissoes['Fornecedores'].append(perm)
            elif perm.codename in vendedores_perms: grupo_permissoes['Vendedores'].append(perm)
            elif 'usuario' in perm.codename: grupo_permissoes['Usuários'].append(perm)
            elif perm.codename in produtos_perms: grupo_permissoes['Produtos'].append(perm)
            elif 'cliente' in perm.codename: grupo_permissoes['Clientes'].append(perm)
            elif perm.codename in orcamentos_perms: grupo_permissoes['Orçamentos'].append(perm)
            elif 'tecnico' in perm.codename: grupo_permissoes['Técnicos'].append(perm)
        self.grupo_permissoes = grupo_permissoes
    # ✅ VALIDAÇÃO EXTRA À PROVA DE ERROS
    def clean_filial_user(self):
        codigo_enviado = self.cleaned_data.get('filial_user')
        if not codigo_enviado:
            raise forms.ValidationError("Por favor, selecione uma filial.")
        if not self.empresa:
            raise forms.ValidationError("Erro: empresa não definida no formulário.")
        try:
            filial = Filial.objects.get(codigo=codigo_enviado, vinc_emp=self.empresa)
        except Filial.DoesNotExist:
            raise forms.ValidationError("A filial selecionada não existe para a sua empresa.")
        if filial.situacao != 'Ativa':
            raise forms.ValidationError("A filial selecionada não está ativa.")
        # Retornamos o objeto Filial completo. O Django vai saber salvar no banco!
        return filial
    def save(self, commit=True):
        user = super().save(commit=False)
        senha_lib = self.cleaned_data.get('senha_liberacao')
        nova_senha = self.cleaned_data.get('password')
        if nova_senha and len(nova_senha.strip()) > 0:
            user.set_password(nova_senha)
        elif user.pk:
            user.password = Usuario.objects.get(pk=user.pk).password

        if senha_lib and len(senha_lib.strip()) > 0:
            user.set_senha_liberacao(senha_lib)
        elif user.pk:
            user.senha_liberacao = Usuario.objects.get(pk=user.pk).senha_liberacao
        user.filial_user = self.cleaned_data.get('filial_user')
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
        fields = ('is_active', 'first_name', 'username', 'email', 'password', 'groups', 'user_permissions')
    def __init__(self, *args, **kwargs):
        super(UsuarioReadOnlyForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.disabled = True