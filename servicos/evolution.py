import os
import base64
import requests

EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY")

def _configurar():
    if not EVOLUTION_API_URL:
        raise RuntimeError("EVOLUTION_API_URL não configurada.")
    if not EVOLUTION_API_KEY:
        raise RuntimeError("EVOLUTION_API_KEY não configurada.")

def _headers():
    return {"apikey": EVOLUTION_API_KEY,"Content-Type": "application/json",}

def _fazer_requisicao(method, url, **kwargs):
    try:
        response = requests.request(method,url,headers=_headers(),timeout=30,**kwargs,)
        response.raise_for_status()
    except requests.Timeout:
        raise RuntimeError("Tempo esgotado ao conectar com a Evolution API.")
    except requests.ConnectionError:
        raise RuntimeError("Não foi possível conectar com a Evolution API.")
    except requests.HTTPError:
        try:
            detalhe = response.json()
        except ValueError:
            detalhe = response.text
        raise RuntimeError(f"Evolution API retornou erro HTTP {response.status_code}: {detalhe}")
    except requests.RequestException as e:
        raise RuntimeError(f"Erro ao comunicar com a Evolution API: {e}")
    try:
        return response.json()
    except ValueError:
        raise RuntimeError("A Evolution API retornou uma resposta inválida.")
# INSTÂNCIAS
def criar_instancia(instancia):
    """ Cria uma nova instância na Evolution API. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/create")
    payload = {"instanceName": instancia,"integration": "WHATSAPP-BAILEYS","qrcode": True,}
    return _fazer_requisicao("POST",url,json=payload,)

def obter_qrcode(instancia):
    """ Obtém o QR Code da instância para conexão. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/connect/{instancia}")
    return _fazer_requisicao("GET",url,)

def verificar_conexao(instancia):
    """ Verifica o estado atual da instância. Possíveis estados: - open, - connecting, - close """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/connectionState/{instancia}")
    return _fazer_requisicao("GET",url,)

def reiniciar_instancia(instancia):
    """ Reinicia uma instância existente. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/restart/{instancia}")
    return _fazer_requisicao("PUT",url,)

def desconectar_instancia(instancia):
    """ Desconecta o WhatsApp da instância, mantendo a instância cadastrada na Evolution. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/logout/{instancia}")
    return _fazer_requisicao("DELETE",url,)

def excluir_instancia(instancia):
    """ Exclui completamente a instância da Evolution API. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/delete/{instancia}")
    return _fazer_requisicao("DELETE",url,)

def listar_instancias():
    """ Lista as instâncias existentes na Evolution API. """
    _configurar()
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/instance/fetchInstances")
    return _fazer_requisicao("GET",url,)
# MENSAGENS
def enviar_texto(instancia, numero, texto):
    """ Envia uma mensagem de texto pelo WhatsApp. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/message/sendText/{instancia}")
    payload = {"number": str(numero),"text": str(texto),}
    return _fazer_requisicao("POST",url,json=payload,)

def enviar_pdf(instancia,numero,pdf_bytes,nome_arquivo,legenda=None):
    """ Envia um PDF pelo WhatsApp através da Evolution API.
    instancia: Nome da instância Evolution que fará o envio.
    numero: Número do destinatário.
    pdf_bytes: Conteúdo binário do PDF.
    nome_arquivo: Nome que aparecerá para o cliente.
    legenda: Texto opcional enviado junto ao documento. """
    _configurar()
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    url = (f"{EVOLUTION_API_URL.rstrip('/')}/message/sendMedia/{instancia}")
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    payload = {"number": str(numero),"mediatype": "document","mimetype": "application/pdf","caption": legenda or "","media": pdf_base64,"fileName": nome_arquivo,}
    return _fazer_requisicao("POST",url,json=payload,)

def garantir_instancia_evolution(instancia):
    """ Garante que a instância exista na Evolution API. Se já existir, não faz nada. Se não existir, cria. """
    instancia = str(instancia).strip()
    if not instancia:
        raise RuntimeError("Nome da instância não informado.")
    existentes = listar_instancias()
    nomes_existentes = {item.get("name") for item in existentes if item.get("name")}
    if instancia in nomes_existentes:
        return {"existe": True,"criada": False,"instancia": instancia,        }
    resposta = criar_instancia(instancia)
    return {"existe": False,"criada": True,"instancia": instancia,"resposta": resposta,}