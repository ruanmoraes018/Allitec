from collections import OrderedDict

ORDEM_CODENAME = [
    'view_tabelapreco', 'add_tabelapreco', 'change_tabelapreco', 'delete_tabelapreco',
    'view_formapgto', 'add_formapgto', 'change_formapgto', 'delete_formapgto',
    'view_tipocobranca', 'add_tipocobranca', 'change_tipocobranca', 'delete_tipocobranca',
    'view_usuario', 'add_usuario', 'change_usuario', 'delete_usuario',
    # resto…
]

GRUPOS_PERMISSOES = OrderedDict({
    'Bairros': ['bairro'],
    'Cidades': ['cidade'],
    'Estados': ['estado'],
    'Clientes': ['cliente'],
    'Produtos': ['produto'],
    'Usuários': ['usuario'],
    'Pedidos': ['pedido'],
    'Orçamentos': ['orcamento'],
    'Técnicos': ['tecnico'],
})
