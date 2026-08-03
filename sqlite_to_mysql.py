import sqlite3
import pymysql


# ================= CONFIGURAÇÕES =================

SQLITE_DB = "db.sqlite3"

MYSQL = {
    "host": "allitec.mysql.pythonanywhere-services.com",
    "user": "allitec",
    "password": "MinhaSenha123",
    "database": "allitec$erp",
    "charset": "utf8mb4",
    "autocommit": False,
}


# ================= ORDEM DE IMPORTAÇÃO =================

ORDEM = [

    # Base
    "empresas_empresa",

    "estados_estado",
    "cidades_cidade",
    "bairros_bairro",

    # Filiais
    "filiais_filial",
    "filiais_usuario",

    # Cadastros
    "grupos_grupo",
    "formas_pgto_formapgto",
    "tipo_cobranca_tipocobranca",
    "bancos_banco",

    "unidades_unidade",
    "marcas_marca",

    # Fornecedores
    "fornecedores_fornecedor",

    # Produtos
    "produtos_produto",
    "produtos_codigoproduto",
    "produtos_produtofornecedor",

    "tabelas_preco_tabelapreco",
    "produtos_produtotabela",

    # Clientes
    "clientes_cliente",
    "clientes_creditocliente",

    # Contratos
    "contratos_contrato",

    # Mensalidades
    "mensalidades_mensalidade",
    "mensalidades_cobrancapix",
    "mensalidades_cobrancapix_mensalidades",

    # Orçamentos
    "orcamentos_orcamento",
    "orcamentos_portaorcamento",
    "orcamentos_portaproduto",
    "orcamentos_portaadicional",
    "orcamentos_orcamentoformapgto",

    # Pedidos
    "pedidos_pedido",
    "pedidos_pedidoproduto",
    "pedidos_pedidoformapgto",
    "pedidos_pagamento",

    # Entradas
    "entradas_entrada",
    "entradas_entradaproduto",
    "entradas_entradaprodutotabela",

    # Financeiro
    "contas_receber_contareceber",
    "contas_receber_contareceberbaixaforma",

    # PDV
    "pdvs_pdv",
    "lancpdvs_caixa",
    "lancpdvs_caixamovimento",

    # Regras
    "regras_produto_regraproduto",

]


# ================= TABELAS IGNORADAS =================

IGNORAR = [
    "django_migrations",
    "django_content_type",
    "auth_permission",
    "auth_group",
    "auth_group_permissions",
    "django_admin_log",
    "django_session",
]


# ================= CONEXÕES =================

sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()


mysql_conn = pymysql.connect(**MYSQL)
mysql_cur = mysql_conn.cursor()


# ================= LIMPA MYSQL =================

print("Limpando banco MySQL...")

mysql_cur.execute("SET FOREIGN_KEY_CHECKS=0")

for tabela in ORDEM:
    try:
        mysql_cur.execute(
            f"DELETE FROM `{tabela}`"
        )
        print(f" Limpou {tabela}")

    except Exception:
        pass


mysql_conn.commit()


# ================= VERIFICA TABELAS =================

sqlite_cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name NOT LIKE 'sqlite_%'
""")

sqlite_tables = {
    r["name"]
    for r in sqlite_cur.fetchall()
}


mysql_cur.execute("SHOW TABLES")

mysql_tables = {
    r[0]
    for r in mysql_cur.fetchall()
}


print()
print(f"Tabelas SQLite: {len(sqlite_tables)}")
print(f"Tabelas MySQL : {len(mysql_tables)}")
print()


# ================= IMPORTAÇÃO =================

for table in ORDEM:


    if table in IGNORAR:
        continue


    if table not in sqlite_tables:
        print(f"IGNORADA (não existe SQLite): {table}")
        continue


    if table not in mysql_tables:
        print(f"IGNORADA (não existe MySQL): {table}")
        continue



    print(f"\nCopiando {table}...")


    sqlite_cur.execute(
        f"SELECT * FROM `{table}`"
    )

    rows = sqlite_cur.fetchall()


    if not rows:
        print("   sem registros")
        continue



    # Colunas SQLite

    sqlite_cols = set(
        rows[0].keys()
    )


    # Colunas MySQL

    mysql_cur.execute(
        f"SHOW COLUMNS FROM `{table}`"
    )

    mysql_cols = {
        x[0]
        for x in mysql_cur.fetchall()
    }



    # somente colunas existentes nos dois

    cols = [
        c
        for c in rows[0].keys()
        if c in mysql_cols
    ]


    if not cols:
        print("   sem colunas compatíveis")
        continue



    campos = ",".join(
        f"`{c}`"
        for c in cols
    )


    valores = ",".join(
        ["%s"] * len(cols)
    )


    sql = f"""
        INSERT INTO `{table}`
        ({campos})
        VALUES ({valores})
    """



    dados = []


    for row in rows:

        dados.append(
            tuple(
                row[c]
                for c in cols
            )
        )



    try:

        mysql_cur.executemany(
            sql,
            dados
        )


        mysql_conn.commit()


        print(
            f"   OK -> {len(dados)} registros"
        )


    except Exception as e:

        mysql_conn.rollback()

        print(
            f"   ERRO -> {e}"
        )



# ================= FINAL =================


mysql_cur.execute(
    "SET FOREIGN_KEY_CHECKS=1"
)

mysql_conn.commit()


sqlite_conn.close()
mysql_conn.close()


print("\n======================")
print("IMPORTAÇÃO FINALIZADA")
print("======================")