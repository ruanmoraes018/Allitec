from core.pagamentos.services import PagamentoService
from pedidos.models import Pagamento
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType

def gerar_pagamentos_caixa(caixa):
    pagamentos_gerados = []
    # 🔥 pega só entradas de venda (ignora sangria, suprimento, etc.)
    movimentos = caixa.movimentos.filter(tipo='Entrada', categoria='Venda')
    # 🔥 agrupa por forma de pagamento
    resumo = {}
    for mov in movimentos:
        forma = mov.forma_pagamento
        if forma.id not in resumo:
            resumo[forma.id] = {"forma": forma, "valor": Decimal("0")}
        resumo[forma.id]["valor"] += mov.valor
    # 🔥 gera pagamento só das formas com gateway
    for item in resumo.values():
        forma = item["forma"]
        valor = item["valor"]
        gateway = (forma.gateway or "").strip().lower()
        if gateway in ["", "nenhum", "none"]: continue
        try:
            service = PagamentoService(forma)
            result = service.gerar_pagamento(valor=valor, descricao=f"Venda Caixa {caixa.codigo}", email=None, external_reference=str(caixa.codigo))
            if not result: continue
            txid = result.get("id")
            qr_code = result.get("qr_code")
            if not txid or not qr_code: continue
            pagamento = Pagamento.objects.create(
                vinc_emp=caixa.vinc_emp, content_type=ContentType.objects.get_for_model(caixa), object_id=caixa.id, forma_pgto=forma, valor=valor, txid=txid, qr_code=qr_code,
                qr_base64=result.get("qr_base64"), gateway=forma.gateway, status="pendente"
            )
            pagamentos_gerados.append({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(pagamento.valor)})
        except Exception: continue
    return pagamentos_gerados

def gerar_pagamentos_pedido(pedido):
    import traceback  # 👈 Importante para ler o rastreamento do erro
    import sys
    pagamentos_gerados = []
    for forma in pedido.formas_pgto.all():
        gateway = (forma.forma_pgto.gateway or "").strip().lower()
        if gateway in ["nenhum", "", "none"]:
            raise Exception(f"Gateway inválido: '{gateway}'")
        try:
            service = PagamentoService(forma.forma_pgto)
            cpf = "".join(filter(str.isdigit, str(getattr(pedido.cli, "cpf_cnpj", "") or "")))

            result = service.gerar_pagamento(
                valor=forma.valor,
                descricao=f"Pedido {pedido.codigo}",
                nome=pedido.cli.razao_social,
                email=pedido.cli.email,
                cpf="".join(filter(str.isdigit, pedido.cli.cpf_cnpj or "")),
                external_reference=str(pedido.codigo)
            )
            if not result:
                raise Exception(
                    f"O PagamentoService retornou None. Gateway={gateway}"
                )
            txid = result.get("id")
            qr_code = result.get("qr_code")
            if not txid or not qr_code:
                raise Exception(
                    f"Resposta incompleta.\n"
                    f"txid={txid}\n"
                    f"qr_code={qr_code}\n"
                    f"result={result}"
                )
            pagamento = Pagamento.objects.create(
                vinc_emp=pedido.vinc_emp,
                content_type=ContentType.objects.get_for_model(pedido),
                object_id=pedido.id,
                forma_pgto=forma.forma_pgto,
                valor=Decimal(str(forma.valor)),
                txid=txid,
                qr_code=qr_code,
                qr_base64=result.get("qr_base64"),
                gateway=forma.forma_pgto.gateway,
                status="pendente",
                gateway_txid=result.get("gateway_id"),
            )
            pagamentos_gerados.append({
                "txid": pagamento.txid,
                "qr_code": pagamento.qr_code,
                "qr_base64": result.get("qr_base64"),
                "valor": str(pagamento.valor)
            })
        except Exception as e:
            # 🔥 ISSO AQUI VAI GRAVAR O ERRO REAL NO SEU SERVER LOG DO PYTHONANYWHERE
            print("\n" + "="*50, file=sys.stderr)
            print(f"CRASH REAL NO FLUXO DE PAGAMENTO ({gateway}): {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("="*50 + "\n", file=sys.stderr)
            raise Exception(str(e))
    return pagamentos_gerados

def gerar_pagamento_conta_receber(conta, forma, valor):
    gateway = (forma.gateway or "").strip().lower()
    if gateway in ["", "nenhum", "none"]: return None
    service = PagamentoService(forma)
    result = service.gerar_pagamento(valor=valor, descricao=f"Conta {conta.num_conta}", email=getattr(conta.cliente, "email", None), external_reference=str(conta.id))
    if not result: return None
    pagamento = Pagamento.objects.create(
        content_type=ContentType.objects.get_for_model(conta), object_id=conta.id, vinc_emp=conta.vinc_emp, forma_pgto=forma, valor=valor, txid=result.get("id"),
        qr_code=result.get("qr_code"), qr_base64=result.get("qr_base64"), gateway=forma.gateway, status="pendente"
    )
    return pagamento

def gerar_pagamentos_orcamento(orcamento):
    pagamentos_gerados = []
    for forma in orcamento.formas_pgto.all():
        gateway = (forma.formas_pgto.gateway or "").strip().lower()
        if gateway in ["", "nenhum", "none"]: continue
        try:
            service = PagamentoService(forma.formas_pgto)
            result = service.gerar_pagamento(valor=forma.valor, descricao=f"Orçamento {orcamento.codigo}", email=getattr(orcamento.cli, "email", None),
                external_reference=str(orcamento.codigo)
            )
            if not result: continue
            txid = result.get("id")
            qr_code = result.get("qr_code")
            if not txid or not qr_code: continue
            pagamento = Pagamento.objects.create(
                vinc_emp=orcamento.vinc_emp, content_type=ContentType.objects.get_for_model(orcamento), object_id=orcamento.id, forma_pgto=forma.formas_pgto, valor=Decimal(str(forma.valor)),
                txid=txid, qr_code=qr_code, qr_base64=result.get("qr_base64"), gateway=forma.formas_pgto.gateway, status="pendente"
            )
            pagamentos_gerados.append({"txid": pagamento.txid, "qr_code": pagamento.qr_code, "qr_base64": pagamento.qr_base64, "valor": str(pagamento.valor)})
        except Exception: continue
    return pagamentos_gerados