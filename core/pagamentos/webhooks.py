from pedidos.models import Pagamento
import json
import requests

def tratar_webhook_mercadopago(data):
    payment_id = data.get("data", {}).get("id")
    print("ID recebido do webhook:", payment_id)
    if not payment_id:
        return None
    pagamento = Pagamento.objects.select_related(
        'forma_pgto', 'content_type'
    ).filter(txid=str(payment_id)).first()
    print("Pagamento encontrado:", pagamento)
    if not pagamento:
        print("NÃO ENCONTROU O PAGAMENTO")
        return None
    credenciais = pagamento.forma_pgto.credenciais or {}
    access_token = credenciais.get("access_token")
    print("Token:", access_token)
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    print("Status HTTP:", response.status_code)
    print("Resposta:", response.text)
    if response.status_code != 200:
        return None
    payment_info = response.json()
    print("Status do pagamento:", payment_info.get("status"))
    return {
        "txid": str(payment_id),
        "status": "pago" if payment_info.get("status") == "approved" else payment_info.get("status"),
        "payload": payment_info
    }

def tratar_webhook_infinitepay(data):
    txid = data.get("invoice_slug")
    if not txid:
        return None
    return {
        "txid": txid,
        "status": "pago", # Como é um disparo de confirmação, o status é pago
        "payload": data
    }

def tratar_webhook_pix_direto(data):
    pix = data.get("pix", [])
    if not pix: return None
    item = pix[0]
    return {"txid": item.get("txid"), "status": "pago"}

def identificar_gateway(request, data):

    origin = request.headers.get("X-Product-Origin")

    if origin and origin.upper() == "ORDER":
        return "pagbank"

    if "charges" in data and "reference_id" in data:
        return "pagbank"

    if request.GET.get("type") == "payment":
        return "mercadopago"

    if "pix" in data:
        return "pix_direto"

    if "invoice_slug" in data:
        return "infinitepay"

    return None

def processar_webhook(request):
    try:
        data = json.loads(request.body) if request.body else {}
    except:
        data = {}

    if request.GET.get("type") == "payment":
        data = {
            "type": "payment",
            "data": {"id": request.GET.get("data.id")}
        }

    gateway = identificar_gateway(request, data)

    if gateway == "mercadopago":
        result = tratar_webhook_mercadopago(data)

    elif gateway == "pix_direto":
        result = tratar_webhook_pix_direto(data)

    elif gateway == "infinitepay":
        result = tratar_webhook_infinitepay(data)

    elif gateway in ("pagbank", "pagseguro"):
        result = tratar_webhook_pagbank(request, data)

    else:
        return None

    if not result:
        return None

    result["gateway"] = gateway
    return result

import hashlib

def gerar_assinatura(token, raw_body):
    payload = f"{token}-{raw_body}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

import hmac

def validar_webhook(token, raw_body, assinatura_recebida):
    assinatura_calculada = hashlib.sha256(
        f"{token}-{raw_body}".encode("utf-8")
    ).hexdigest()

    return hmac.compare_digest(assinatura_calculada, assinatura_recebida)

def tratar_webhook_pagbank(request, data):

    order_id = data.get("reference_id")  # 👈 FIX PRINCIPAL
    charges = data.get("charges") or []
    status = charges[0].get("status") if charges else None

    if not order_id:
        return None

    pagamento = Pagamento.objects.filter(txid=str(order_id)).first()

    if not pagamento:
        print("PAGAMENTO NÃO ENCONTRADO:", order_id)
        return None

    status_normalizado = "pago" if status == "PAID" else "pendente"

    if status_normalizado == "pago":
        pagamento.status = "pago"
        pagamento.payload = data
        pagamento.save(update_fields=["status", "payload"])

        pedido = pagamento.origem

        if pedido.status_pagamento != "pago":
            pedido.atualizar_status_pagamento()

            if pedido.status_pagamento == "pago" and pedido.situacao == "Aberto":
                pedido.processar_pagamento(None)
                pedido.situacao = "Faturado"
                pedido.save(update_fields=["situacao"])

    return {
        "txid": order_id,
        "status": status_normalizado,
        "payload": data
    }
