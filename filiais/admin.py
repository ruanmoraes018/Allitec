from django.contrib import admin
from .models import Filial, Usuario
from empresas.models import Empresa
from bancos.models import Banco
from produtos.models import Produto, ProdutoTabela, CodigoProduto
from clientes.models import Cliente
from tecnicos.models import Tecnico
from orcamentos.models import Orcamento, PortaOrcamento, PortaProduto, PortaAdicional, OrcamentoFormaPgto
from grupos.models import Grupo
from bairros.models import Bairro
from cidades.models import Cidade
from estados.models import Estado
from marcas.models import Marca
from mensalidades.models import Mensalidade
from entradas.models import Entrada, EntradaProduto
from formas_pgto.models import FormaPgto
from pedidos.models import Pedido, PedidoProduto
from tabelas_preco.models import TabelaPreco

# Inline para mostrar Filiais dentro da Empresa
class FilialInline(admin.TabularInline):
    model = Filial
    extra = 0
    fields = ('fantasia', 'cnpj', 'cidade_fil', 'uf')
    show_change_link = True

class MensalidadeInline(admin.TabularInline):
    model = Mensalidade
    extra = 0
    fields = ('num_mens', 'situacao', 'empresa', 'empresa_fantasia', 'created_at', 'dt_venc', 'vl_mens')
    readonly_fields = ('created_at', 'empresa_fantasia')
    show_change_link = True

    def empresa_fantasia(self, obj):
        return obj.empresa.fantasia if obj.empresa else '-'
    empresa_fantasia.short_description = 'Fantasia'

class BancoInline(admin.TabularInline):
    model = Banco
    extra = 0
    fields = ('nome_banco', 'cod_banco')
    show_change_link = True

# class OrcamentoInline(admin.TabularInline):
#     model = Orcamento
#     extra = 0
#     fields = ('num_orcamento', 'cli', 'situacao', 'dt_emi', 'desconto')
#     show_change_link = True

class ClienteInline(admin.TabularInline):
    model = Cliente
    extra = 0
    fields = ('fantasia', 'cpf_cnpj', 'situacao')
    show_change_link = True

class TecnicoInline(admin.TabularInline):
    model = Tecnico
    extra = 0
    fields = ('nome', 'tel', 'email')
    show_change_link = True

class CidadeInline(admin.TabularInline):
    model = Cidade
    extra = 0
    fields = ('nome_cidade', 'vinc_emp')
    show_change_link = True

class MarcaInline(admin.TabularInline):
    model = Marca
    extra = 0
    fields = ('nome_marca', 'vinc_emp')
    show_change_link = True

class EstadoInline(admin.TabularInline):
    model = Estado
    extra = 0
    fields = ('nome_estado', 'vinc_emp')
    show_change_link = True

class GrupoInline(admin.TabularInline):
    model = Grupo
    extra = 0
    fields = ('nome_grupo',)
    show_change_link = True

class ProdutoInline(admin.TabularInline):
    model = Produto
    extra = 0
    fields = ('desc_prod', 'grupo', 'unidProd', 'estoque_prod')
    show_change_link = True

class FormaPgtoInline(admin.TabularInline):
    model = FormaPgto
    extra = 0
    fields = ('descricao', 'troco', 'situacao', 'tipo')
    show_change_link = True

class TabelaPrecoInline(admin.TabularInline):
    model = TabelaPreco
    extra = 0
    fields = ('descricao', 'margem')
    show_change_link = True

class BairroInline(admin.TabularInline):
    model = Bairro
    extra = 0
    fields = ('nome_bairro', 'vinc_emp')
    show_change_link = True

class EntradaInline(admin.TabularInline):
    model = Entrada
    extra = 0
    fields = ('fornecedor', 'numeracao', 'dt_emi', 'total')
    show_change_link = True

class PedidoInline(admin.TabularInline):
    model = Pedido
    extra = 0
    fields = ('cli', 'id', 'dt_emi', 'total')
    show_change_link = True

class PedidoProdutoInline(admin.TabularInline):
    model = PedidoProduto
    extra = 0
    fields = ('produto', 'quantidade')
    show_change_link = True

class CodigoProdutoInline(admin.TabularInline):
    model = CodigoProduto
    extra = 0
    fields = ('produto', 'codigo')
    show_change_link = True

class ProdutoTabelaInline(admin.TabularInline):
    model = ProdutoTabela
    extra = 0
    fields = ('produto', 'tabela')
    show_change_link = True

class EntradaProdutoInline(admin.TabularInline):
    model = EntradaProduto
    extra = 0
    fields = ('produto', 'quantidade', 'preco_unitario')
    show_change_link = True

# Admin para Empresa - só filiais inline
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'cnpj')
    search_fields = ('razao_social', 'cnpj')
    inlines = [FilialInline, MensalidadeInline, BancoInline, ClienteInline, TecnicoInline, ProdutoInline, BairroInline, CidadeInline, EstadoInline,
                GrupoInline, FormaPgtoInline, EntradaInline, PedidoInline, MarcaInline, TabelaPrecoInline
    ]

# Inlines para os modelos relacionados à Filial

class UsuarioInline(admin.StackedInline):
    model = Usuario
    extra = 0
    autocomplete_fields = ['empresa']
    show_change_link = True
    filter_horizontal = ('groups', 'user_permissions')  # <-- ajuda a selecionar
    fieldsets = (
        (None, {
            'fields': ('first_name', 'username', 'password', 'empresa', 'filial_user')
        }),
        ('Permissões', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
        }),
    )

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    search_fields = (
        'desc_prod',
        'id',
    )
    
# Admin para Filial - com todos os inlines dos modelos vinculados a ela
@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ('id', 'fantasia', 'cnpj', 'cidade_fil', 'uf')
    search_fields = ('fantasia', 'cnpj')
    inlines = [
         UsuarioInline,
    ]

class PortaProdutoInline(admin.TabularInline):
    model = PortaProduto
    extra = 0
    autocomplete_fields = ['produto']
    readonly_fields = ('subtotalP',)

class PortaAdicionalInline(admin.TabularInline):
    model = PortaAdicional
    extra = 0
    autocomplete_fields = ['produto']
    readonly_fields = ('subtotalA',)

class PortaOrcamentoInline(admin.StackedInline):
    model = PortaOrcamento
    extra = 0
    show_change_link = True
    inlines = []  # Django não suporta inline dentro de inline nativamente


@admin.register(PortaOrcamento)
class PortaOrcamentoAdmin(admin.ModelAdmin):

    list_display = ('orcamento', 'numero', 'largura', 'altura')
    inlines = [PortaProdutoInline, PortaAdicionalInline]

@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):

    list_display = ('num_orcamento', 'cli', 'situacao', 'subtotal', 'total')

    inlines = [
        PortaOrcamentoInline,
    ]

    readonly_fields = (
        'json_portas',
        'json_formas_pgto',
    )

    fieldsets = (
        ('Dados do Orçamento', {
            'fields': (
                'num_orcamento',
                'cli',
                'situacao',
                'subtotal',
                'desconto', 
                'acrescimo', 
                'total',
            )
        }),
        ('🔍 DEBUG – Portas (JSON)', {
            'fields': ('json_portas',),
        }),
        ('💳 DEBUG – Formas de Pagamento (JSON)', {
            'fields': ('json_formas_pgto',),
        }),
    )

    def json_portas(self, obj):
        import json
        from django.utils.html import format_html

        portas = []
        for porta in obj.portas.all():
            portas.append({
                "porta": porta.numero,
                "largura": str(porta.largura),
                "altura": str(porta.altura),
                "produtos": [
                    {
                        "id": pp.produto.id,
                        "descricao": pp.produto.desc_prod,
                        "qtd": str(pp.quantidade),
                        "subtotal": str(pp.subtotal),
                    }
                    for pp in porta.produtos.all()
                ],
                "adicionais": [
                    {
                        "id": ad.produto.id,
                        "descricao": ad.produto.desc_prod,
                        "qtd": str(ad.quantidade),
                        "subtotal": str(ad.subtotal),
                    }
                    for ad in porta.adicionais.all()
                ],
            })

        return format_html(
            "<pre style='white-space: pre-wrap'>{}</pre>",
            json.dumps(portas, indent=2, ensure_ascii=False)
        )

    json_portas.short_description = "Portas / Produtos / Adicionais (JSON)"

    def json_formas_pgto(self, obj):
        import json
        from django.utils.html import format_html

        dados = [
            {
                "forma": fp.formas_pgto.descricao,
                "valor": str(fp.valor),
            }
            for fp in obj.formas_pgto.all()
        ]

        return format_html(
            "<pre style='white-space: pre-wrap'>{}</pre>",
            json.dumps(dados, indent=2, ensure_ascii=False)
        )

    json_formas_pgto.short_description = "Formas de Pagamento (JSON)"
