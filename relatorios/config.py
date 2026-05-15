RELATORIOS = [
    {
        'perm': 'pedidos.relatorio_pedidos', 'titulo': 'Relatório de Pedidos', 'descricao': 'Relatório geral de pedidos faturados por período.', 
        'icone': 'fa-solid fa-file-invoice', 'view_name': 'relatorio_pedidos',
        'filtros': [
            {
                'tipo': 'date', 'name': 'dt_ini', 'id': 'data_inicio1', 'label': 'Dt. Início', 'col': '2'
            },
            {
                'tipo': 'date', 'name': 'dt_fim', 'id': 'data_fim1', 'label': 'Dt. Final', 'col': '2'
            },
            {
                'tipo': 'select', 'name': 'tipo', 'label': 'Tipo', 'col': '2',
                'options': [('resumido', 'Resumido'), ('detalhado', 'Detalhado'),]
            },
            {
                'tipo': 'filial', 'name': 'fil', 'id': 'id_filial_user', 'label': 'Filial', 'col': '3'
            },
            {
                'tipo': 'cliente', 'name': 'cl', 'id': 'cliente', 'label': 'Cliente', 'col': '3'
            },
            {
                'tipo': 'vendedor', 'name': 'vend_r_ped', 'id': 'vendedor_r_ped', 'label': 'Vendedor', 'col': '3'
            },
        ]
    },
    {
        'perm': 'produtos.relatorio_vendas_produto', 'titulo': 'Relatório de Vendas de Produtos', 'descricao': 'Relatórios de Vendas de Produtos.',
        'icone': 'fa-solid fa-boxes-stacked', 'view_name': 'relatorio_vendas_produto',
        'filtros': [
            {
                'tipo': 'date', 'name': 'dt_ini_v_p', 'id': 'data_inicio2', 'label': 'Dt. Início', 'col': '2'
            },
            {
                'tipo': 'date', 'name': 'dt_fim_v_p', 'id': 'data_fim2', 'label': 'Dt. Final', 'col': '2'
            },
            {
                'tipo': 'grupo', 'name': 'grupo', 'id': 'grupo', 'label': 'Grupo', 'col': '4'
            },
            {
                'tipo': 'marca', 'name': 'marca', 'id': 'marca', 'label': 'Marca', 'col': '4'
            },
            {
                'tipo': 'vendedor', 'name': 'vend', 'id': 'vendedor', 'label': 'Vendedor', 'col': '3'
            },
            {
                'tipo': 'select', 'name': 'tipo_v_p', 'label': 'Tipo', 'col': '2',
                'options': [('resumido', 'Resumido'), ('detalhado', 'Detalhado'),]
            },
            {
                'tipo': 'select', 'name': 'ordenacao', 'label': 'Ordem', 'col': '3',
                'options': [('qtd', 'Quantidade Vendida'), ('valor', 'Valor Vendido'), ('descricao', 'Descrição'),]
            },
        ]
    },
]