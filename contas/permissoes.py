from collections import OrderedDict

APPS_PERMISSOES = [
    'formas_pgto','tipo_cobranca','entradas','bairros','cidades','estados','grupos','bancos','unidades','filiais','tabelas_preco','lancpdvs','pdvs','clientes','fornecedores',
    'vendedores','produtos','orcamentos','tecnicos','pedidos','marcas','regras_produto','contas_receber', 'estoques', 'informacoes',
]
ORDEM_CODENAME = [
    'view_caixa','add_caixa','change_caixa','delete_caixa','caixa_outro_user',
    'view_pdv','add_pdv','change_pdv','delete_pdv',
    'view_tabelapreco','add_tabelapreco','change_tabelapreco','delete_tabelapreco',
    'view_formapgto','add_formapgto','change_formapgto','delete_formapgto',
    'view_tipocobranca','add_tipocobranca','change_tipocobranca','delete_tipocobranca',
    'view_entrada','add_entrada','change_entrada','delete_entrada','efetivar_entrada','cancelar_entrada',
    'view_bairro','add_bairro','change_bairro','delete_bairro',
    'view_cidade','add_cidade','change_cidade','delete_cidade',
    'view_estado','add_estado','change_estado','delete_estado',
    'view_grupo','add_grupo','change_grupo','delete_grupo',
    'view_unidade','add_unidade','change_unidade','delete_unidade',
    'view_banco','add_banco','change_banco','delete_banco',
    'view_filial','add_filial','change_filial','delete_filial',
    'view_usuario','add_usuario','change_usuario','delete_usuario',
    'view_produto','add_produto','change_produto','clonar_produto','delete_produto','relatorio_vendas_produto',
    'view_cliente','add_cliente','change_cliente','delete_cliente',
    'view_fornecedor','add_fornecedor','change_fornecedor','delete_fornecedor',
    'view_vendedor','add_vendedor','change_vendedor','delete_vendedor',
    'view_orcamento','add_orcamento','change_orcamento','clonar_orcamento','delete_orcamento','atribuir_desconto','atribuir_acrescimo','faturar_orcamento','cancelar_orcamento','alterar_dt_venc_orc','alterar_dt_fat_orc','vender_sem_estoque_orc',
    'view_tecnico','add_tecnico','change_tecnico','delete_tecnico',
    'view_marca','add_marca','change_marca','delete_marca',
    'view_regraproduto','add_regraproduto','change_regraproduto','delete_regraproduto',
    'view_pedido','add_pedido','change_pedido','delete_pedido','clonar_pedido','atribuir_desconto_ped','atribuir_acrescimo_ped','faturar_pedido','cancelar_pedido','vender_sem_estoque_ped','alt_vl_ped','alterar_data_faturamento','relatorio_pedidos',
    'view_contareceber','add_contareceber','change_contareceber','delete_contareceber','atribuir_desconto_cr','baixar_cr','estornar_cr',
    'view_estoque', 'add_estoque', 'change_estoque', 'delete_estoque',
    'view_informacoes', 'add_informacoes', 'change_informacoes', 'delete_informacoes',
    'view_gruporegraproduto', 'add_gruporegraproduto', 'change_gruporegraproduto', 'delete_gruporegraproduto',
]
ORDEM_MAP = {codename: indice for indice, codename in enumerate(ORDEM_CODENAME)}
CATEGORIAS_PERMISSOES = OrderedDict({
    'Complementos': [
        'Bairros','Bancos','Cidades','Estados','Grupos','Marcas','Unidades','Tabelas de Preço','Tipos de Cobrança','Formas de Pagamento','Regras de Produto','Estoques',
        'Informações', 'Grupo de Regras',
    ],
    'Cadastros': [
        'Clientes','Filiais','Fornecedores','Produtos','Técnicos','Usuários','Vendedores','PDVs'
    ],
    'Estoque': [
        'Entradas de NF/Pedidos'
    ],
    'Faturamento': [
        'Pedidos','Caixas','Orçamentos'
    ],
    'Financeiro': [
        'Contas à Receber'
    ]
})
GRUPOS_PERMISSOES = OrderedDict({
    'Caixas': ['view_caixa','add_caixa','change_caixa','delete_caixa','caixa_outro_user'],
    'PDVs': ['view_pdv','add_pdv','change_pdv','delete_pdv'],
    'Tabelas de Preço': ['view_tabelapreco','add_tabelapreco','change_tabelapreco','delete_tabelapreco'],
    'Formas de Pagamento': ['view_formapgto','add_formapgto','change_formapgto','delete_formapgto'],
    'Tipos de Cobrança': ['view_tipocobranca','add_tipocobranca','change_tipocobranca','delete_tipocobranca'],
    'Entradas de NF/Pedidos': ['view_entrada','add_entrada','change_entrada','delete_entrada','efetivar_entrada','cancelar_entrada'],
    'Bairros': ['view_bairro','add_bairro','change_bairro','delete_bairro'],
    'Cidades': ['view_cidade','add_cidade','change_cidade','delete_cidade'],
    'Estados': ['view_estado','add_estado','change_estado','delete_estado'],
    'Estoques': ['view_estoque', 'add_estoque', 'change_estoque', 'delete_estoque'],
    'Informações': ['view_informacoes', 'add_informacoes', 'change_informacoes', 'delete_informacoes'],
    'Grupos': ['view_grupo','add_grupo','change_grupo','delete_grupo'],
    'Bancos': ['view_banco','add_banco','change_banco','delete_banco'],
    'Unidades': ['view_unidade','add_unidade','change_unidade','delete_unidade'],
    'Filiais': ['view_filial','add_filial','change_filial','delete_filial'],
    'Usuários': ['view_usuario','add_usuario','change_usuario','delete_usuario'],
    'Produtos': ['view_produto','add_produto','change_produto','clonar_produto','delete_produto','relatorio_vendas_produto'],
    'Clientes': ['view_cliente','add_cliente','change_cliente','delete_cliente'],
    'Fornecedores': ['view_fornecedor','add_fornecedor','change_fornecedor','delete_fornecedor'],
    'Vendedores': ['view_vendedor','add_vendedor','change_vendedor','delete_vendedor'],
    'Orçamentos': [
        'view_orcamento','add_orcamento','change_orcamento','clonar_orcamento','delete_orcamento','atribuir_desconto','atribuir_acrescimo','faturar_orcamento',
        'cancelar_orcamento','alterar_dt_venc_orc','alterar_dt_fat_orc','vender_sem_estoque_orc'
    ],
    'Técnicos': ['view_tecnico','add_tecnico','change_tecnico','delete_tecnico'],
    'Marcas': ['view_marca','add_marca','change_marca','delete_marca'],
    'Regras de Produto': ['view_regraproduto','add_regraproduto','change_regraproduto','delete_regraproduto'],
    'Pedidos': [
        'view_pedido','add_pedido','change_pedido','delete_pedido','clonar_pedido','atribuir_desconto_ped','atribuir_acrescimo_ped','faturar_pedido','cancelar_pedido',
        'vender_sem_estoque_ped','alt_vl_ped','alterar_data_faturamento','relatorio_pedidos'
    ],
    'Contas à Receber': ['view_contareceber','add_contareceber','change_contareceber','delete_contareceber','atribuir_desconto_cr','baixar_cr','estornar_cr'],
    'Grupo de Regras': ['view_gruporegraproduto', 'add_gruporegraproduto', 'change_gruporegraproduto', 'delete_gruporegraproduto',],
})
def agrupar_permissoes_por_grupo(permissoes):
    grupos = OrderedDict((grupo, []) for grupo in GRUPOS_PERMISSOES)
    for perm in permissoes:
        for grupo, codenames in GRUPOS_PERMISSOES.items():
            if perm.codename in codenames:
                grupos[grupo].append(perm)
                break
    return grupos