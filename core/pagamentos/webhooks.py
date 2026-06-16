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
    """
    Trata o retorno do webhook da InfinitePay conforme documentação oficial:
    { "invoice_slug": "abc123", "paid_amount": 1010, "capture_method": "pix", ... }
    """
    # O 'invoice_slug' é o código da fatura que guardamos no campo 'txid' do banco
    txid = data.get("invoice_slug")
    if not txid:
        return None

    # Se o webhook chegou aqui, é porque o pagamento foi aprovado/pago pelo cliente
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
    if request.GET.get("type") == "payment": return "mercadopago"
    if data.get("type") == "payment": return "mercadopago"
    if "pix" in data: return "pix_direto"
    if "reference_id" in data and "status" in data: return "pagbank"

    # 🚀 Identifica InfinitePay pelo 'invoice_slug' ou pelos campos que você listou
    if "invoice_slug" in data or ("capture_method" in data and "paid_amount" in data):
        return "infinitepay"

    return None

def processar_webhook(request):
    try: data = json.loads(request.body) if request.body else {}
    except: data = {}
    if request.GET.get("type") == "payment": data = {"type": "payment", "data": {"id": request.GET.get("data.id")}}

    gateway = identificar_gateway(request, data)

    if gateway == "mercadopago": result = tratar_webhook_mercadopago(data)
    elif gateway == "pix_direto": result = tratar_webhook_pix_direto(data)
    elif gateway == "infinitepay": result = tratar_webhook_infinitepay(data)
    elif gateway == "pagbank": result = processar_webhook_pagbank(request) # 👈 Chama o do PagBank aqui!
    else: return None

    if not result: return None
    result["gateway"] = gateway
    return result

def processar_webhook_pagbank(request):
    """
    Trata o payload plano do PagBank e padroniza o retorno
    para o formato aceito pelo banco de dados do sistema.
    """
    try:
        import json
        payload = json.loads(request.body.decode('utf-8'))

        txid = payload.get('reference_id')
        status_pagbank = payload.get('status')
        status_map = {
            "PAID": "pago",
            "AUTHORIZED": "pago",
            "WAITING": "pendente",
            "CANCELED": "cancelado"
        }

        status_interno = status_map.get(status_pagbank, "pendente")

        if not txid:
            return None

        return {
            "txid": txid,
            "status": status_interno,
            "payload": payload  # Salva o JSON bruto do PagBank no campo payload
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Erro PagBank:", e)
        return None