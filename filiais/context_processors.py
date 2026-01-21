# context_processors.py
from django.contrib.auth.models import Permission
from notifications.models import Notification

def notificacoes(request):
    if request.user.is_authenticated:
        notificacoes = Notification.objects.filter(recipient=request.user, unread=True)
        return {'notificacoes': notificacoes}
    return {'notificacoes': []}

# context_processors.py
def user_permissions(request):
    if request.user.is_authenticated:
        permissoes = request.user.get_all_permissions()
        return {
            # Empresas somente quem for autorizado
            'perm_view_empresa': 'empresas.view_empresa' in permissoes,
            'perm_add_empresa': 'empresas.add_empresa' in permissoes,
            'perm_change_empresa': 'empresas.change_empresa' in permissoes,
            'perm_delete_empresa': 'empresas.delete_empresa' in permissoes,
            # Contratos somente quem for autorizado
            'perm_view_contrato': 'contratos.view_contrato' in permissoes,
            'perm_add_contrato': 'contratos.add_contrato' in permissoes,
            'perm_change_contrato': 'contratos.change_contrato' in permissoes,
            'perm_delete_contrato': 'contratos.delete_contrato' in permissoes,
            # Mensalidades somente quem for autorizado
            'perm_view_mensalidade': 'mensalidades.view_mensalidade' in permissoes,
            'perm_add_mensalidade': 'mensalidades.add_mensalidade' in permissoes,
            'perm_change_mensalidade': 'mensalidades.change_mensalidade' in permissoes,
            'perm_delete_mensalidade': 'mensalidades.delete_mensalidade' in permissoes,
            # Filiais
            'perm_view_filial': 'filiais.view_filial' in permissoes,
            'perm_add_filial': 'filiais.add_filial' in permissoes,
            'perm_change_filial': 'filiais.change_filial' in permissoes,
            'perm_delete_filial': 'filiais.delete_filial' in permissoes,
            # Usuários
            'perm_view_usuario': 'filiais.view_usuario' in permissoes,
            'perm_add_usuario': 'filiais.add_usuario' in permissoes,
            'perm_change_usuario': 'filiais.change_usuario' in permissoes,
            'perm_delete_usuario': 'filiais.delete_usuario' in permissoes,
            # Produtos
            'perm_view_produtos': 'produtos.view_produto' in permissoes,
            'perm_add_produto': 'produtos.add_produto' in permissoes,
            'perm_change_produto': 'produtos.change_produto' in permissoes,
            'perm_clonar_produto': 'produtos.clonar_produto' in permissoes,
            'perm_delete_produto': 'produtos.delete_produto' in permissoes,
            # Clientes
            'perm_view_clientes': 'clientes.view_cliente' in permissoes,
            'perm_add_cliente': 'clientes.add_cliente' in permissoes,
            'perm_change_cliente': 'clientes.change_cliente' in permissoes,
            'perm_delete_cliente': 'clientes.delete_cliente' in permissoes,
            # Fornecedores
            'perm_view_fornecedores': 'fornecedores.view_fornecedor' in permissoes,
            'perm_add_fornecedor': 'fornecedores.add_fornecedor' in permissoes,
            'perm_change_fornecedor': 'fornecedores.change_fornecedor' in permissoes,
            'perm_delete_fornecedor': 'fornecedores.delete_fornecedor' in permissoes,
            # Orçamentos
            'perm_view_orcamentos': 'orcamentos.view_orcamento' in permissoes,
            'perm_add_orcamento': 'orcamentos.add_orcamento' in permissoes,
            'perm_change_orcamento': 'orcamentos.change_orcamento' in permissoes,
            'perm_clonar_orcamento': 'orcamentos.clonar_orcamento' in permissoes,
            'perm_delete_orcamento': 'orcamentos.delete_orcamento' in permissoes,
            'perm_faturar_orcamento': 'orcamentos.faturar_orcamento' in permissoes,
            'perm_cancelar_orcamento': 'orcamentos.cancelar_orcamento' in permissoes,
            'perm_atribuir_desconto': 'orcamentos.atribuir_desconto' in permissoes,
            'perm_atribuir_acrescimo': 'orcamentos.atribuir_acrescimo' in permissoes,
            # Técnicos
            'perm_view_tecnicos': 'tecnicos.view_tecnico' in permissoes,
            'perm_add_tecnico': 'tecnicos.add_tecnico' in permissoes,
            'perm_change_tecnico': 'tecnicos.change_tecnico' in permissoes,
            'perm_delete_tecnico': 'tecnicos.delete_tecnico' in permissoes,
            # Bancos
            'perm_view_bancos': 'bancos.view_banco' in permissoes,
            'perm_add_banco': 'bancos.add_banco' in permissoes,
            'perm_change_banco': 'bancos.change_banco' in permissoes,
            'perm_delete_banco': 'bancos.delete_banco' in permissoes,
            # Grupos
            'perm_view_grupos': 'grupos.view_grupo' in permissoes,
            'perm_add_grupo': 'grupos.add_grupo' in permissoes,
            'perm_change_grupo': 'grupos.change_grupo' in permissoes,
            'perm_delete_grupo': 'grupos.delete_grupo' in permissoes,
            # Bairros
            'perm_view_bairros': 'bairros.view_bairro' in permissoes,
            'perm_add_bairro': 'bairros.add_bairro' in permissoes,
            'perm_change_bairro': 'bairros.change_bairro' in permissoes,
            'perm_delete_bairro': 'bairros.delete_bairro' in permissoes,
            # Cidades
            'perm_view_cidades': 'cidades.view_cidade' in permissoes,
            'perm_add_cidade': 'cidades.add_cidade' in permissoes,
            'perm_change_cidade': 'cidades.change_cidade' in permissoes,
            'perm_delete_cidade': 'cidades.delete_cidade' in permissoes,
            # Estados
            'perm_view_estados': 'estados.view_estado' in permissoes,
            'perm_add_estado': 'estados.add_estado' in permissoes,
            'perm_change_estado': 'estados.change_estado' in permissoes,
            'perm_delete_estado': 'estados.delete_estado' in permissoes,
            # Unidades
            'perm_view_unidades': 'unidades.view_unidade' in permissoes,
            'perm_add_unidade': 'unidades.add_unidade' in permissoes,
            'perm_change_unidade': 'unidades.change_unidade' in permissoes,
            'perm_delete_unidade': 'unidades.delete_unidade' in permissoes,
            #Entradas de NF/Pedidos
            'perm_view_entradas': 'entradas.view_entrada' in permissoes,
            'perm_add_entrada': 'entradas.add_entrada' in permissoes,
            'perm_change_entrada': 'entradas.change_entrada' in permissoes,
            'perm_delete_entrada': 'entradas.delete_entrada' in permissoes,
            #Tipos de Cobranças
            'perm_view_tipocobranca': 'tipo_cobranca.view_tipocobranca' in permissoes,
            'perm_add_tipocobranca': 'tipo_cobranca.add_tipocobranca' in permissoes,
            'perm_change_tipocobranca': 'tipo_cobranca.change_tipocobranca' in permissoes,
            'perm_delete_tipocobranca': 'tipo_cobranca.delete_tipocobranca' in permissoes,
            #Formas de Pagamentos
            'perm_view_formapgto': 'formas_pgto.view_formapgto' in permissoes,
            'perm_add_formapgto': 'formas_pgto.add_formapgto' in permissoes,
            'perm_change_formapgto': 'formas_pgto.change_formapgto' in permissoes,
            'perm_delete_formapgto': 'formas_pgto.delete_formapgto' in permissoes,
            #Pedidos
            'perm_view_pedido': 'pedidos.view_pedido' in permissoes,
            'perm_add_pedido': 'pedidos.add_pedido' in permissoes,
            'perm_change_pedido': 'pedidos.change_pedido' in permissoes,
            'perm_delete_pedido': 'pedidos.delete_pedido' in permissoes,
            'perm_atribuir_desconto_ped': 'pedidos.atribuir_desconto_ped' in permissoes,
            'perm_atribuir_acrescimo_ped': 'pedidos.atribuir_acrescimo_ped' in permissoes,
            'perm_faturar_pedido': 'pedidos.faturar_pedido' in permissoes,
            'perm_cancelar_pedido': 'pedidos.cancelar_pedido' in permissoes,
            'perm_clonar_pedido': 'pedidos.clonar_pedido' in permissoes,
            #Marcas
            'perm_view_marcas': 'marcas.view_marca' in permissoes,
            'perm_add_marca': 'marcas.add_marca' in permissoes,
            'perm_change_marca': 'marcas.change_marca' in permissoes,
            'perm_delete_marca': 'marcas.delete_marca' in permissoes,
            #Tabelas de Preço
            'perm_view_tabelapreco': 'tabelas_preco.view_tabelapreco' in permissoes,
            'perm_add_tabelapreco': 'tabelas_preco.add_tabelapreco' in permissoes,
            'perm_change_tabelapreco': 'tabelas_preco.change_tabelapreco' in permissoes,
            'perm_delete_tabelapreco': 'tabelas_preco.delete_tabelapreco' in permissoes,
            #Regras de Produto
            'perm_view_regraproduto': 'regras_produto.view_regraproduto' in permissoes,
            'perm_add_regraproduto': 'regras_produto.add_regraproduto' in permissoes,
            'perm_change_regraproduto': 'regras_produto.change_regraproduto' in permissoes,
            'perm_delete_regraproduto': 'regras_produto.delete_regraproduto' in permissoes,
        }
    return {}
