import mercadopago
from pedidos.models import Pagamento
import json

import requests

def tratar_webhook_mercadopago(data):
    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return None
    pagamento = Pagamento.objects.select_related('forma_pgto').filter(txid=str(payment_id)).first()
    if not pagamento:
        return None
    credenciais = pagamento.forma_pgto.credenciais or {}
    access_token = credenciais.get("access_token")
    if not access_token:
        return None
    url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    payment_info = response.json()
    status = payment_info.get("status")
    return {"txid": str(payment_id), "status": "pago" if status == "approved" else status, "payload": payment_info}

def tratar_webhook_pix_direto(data):
    pix = data.get("pix", [])
    if not pix:
        return None
    item = pix[0]
    return {"txid": item.get("txid"), "status": "pago"}

def identificar_gateway(request, data):
    if request.GET.get("type") == "payment":
        return "mercadopago"
    if data.get("type") == "payment":
        return "mercadopago"
    if "pix" in data:
        return "pix_direto"
    return None

def processar_webhook(request):
    try:
        data = json.loads(request.body) if request.body else {}
    except:
        data = {}
    if request.GET.get("type") == "payment":
        data = {"type": "payment", "data": {"id": request.GET.get("data.id")}}
    gateway = identificar_gateway(request, data)
    if gateway == "mercadopago":
        result = tratar_webhook_mercadopago(data)
    elif gateway == "pix_direto":
        result = tratar_webhook_pix_direto(data)
    else:
        return None
    if not result:
        return None
    result["gateway"] = gateway
    return result