import re
from datetime import datetime, timezone
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.x509.oid import NameOID

class CertificadoService:
    def __init__(self, arquivo, senha, cnpj_filial=None):
        self.arquivo = arquivo
        self.senha = senha or ""
        self.cnpj_filial = re.sub(r"\D", "", cnpj_filial or "")
        self.private_key = None
        self.cert = None
        self._carregar()

    def _carregar(self):
        try:
            print("ARQUIVO:", self.arquivo)
            print("TIPO ARQUIVO:", type(self.arquivo))
            print("SENHA USADA:", self.senha)

            self.arquivo.seek(0)
            dados = self.arquivo.read()

            print("TAMANHO CERTIFICADO:", len(dados))

            self.private_key, self.cert, cadeia = load_key_and_certificates(
                dados,
                self.senha.encode()
            )

            if not self.cert:
                raise Exception("Certificado inválido.")

        except ValueError:
            raise Exception("Senha do certificado inválida.")

    def _buscar_subject(self, oid):
        try:
            return self.cert.subject.get_attributes_for_oid(oid)[0].value
        except Exception:
            return ""

    def nome(self):
        return self._buscar_subject(NameOID.COMMON_NAME)

    def cnpj(self):
        serial = self._buscar_subject(NameOID.SERIAL_NUMBER)
        numeros = re.sub(r"\D", "", serial)
        if len(numeros) == 14:
            return numeros
        # fallback caso venha dentro do texto completo
        texto = self.cert.subject.rfc4514_string()
        encontrado = re.search(r"\d{14}", texto)
        if encontrado:
            return encontrado.group()
        return ""

    def cnpj_formatado(self):
        cnpj = self.cnpj()
        if len(cnpj) != 14:
            return ""
        return (f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}")

    def validade(self):
        agora = datetime.now(timezone.utc)
        inicio = self.cert.not_valid_before_utc
        fim = self.cert.not_valid_after_utc
        dias = (fim - agora).days
        return {"inicio": inicio, "fim": fim, "dias_restantes": dias, "valido": inicio <= agora <= fim, "expirado": agora > fim, "ainda_nao_valido": agora < inicio,}

    def possui_chave_privada(self):
        return self.private_key is not None

    def cnpj_confere(self):
        cnpj_filial = re.sub(
            r"\D",
            "",
            self.cnpj_filial or ""
        )
        cnpj_certificado = re.sub(
            r"\D",
            "",
            self.cnpj()
        )
        if not cnpj_filial or not cnpj_certificado:
            return False
        return cnpj_filial == cnpj_certificado

    def resumo(self):
        validade = self.validade()
        return {
            "nome": self.nome(), "cnpj": self.cnpj(), "cnpj_formatado": self.cnpj_formatado(), "inicio_validade": validade["inicio"], "fim_validade": validade["fim"],
            "valido": validade["valido"], "expirado": validade["expirado"], "dias_restantes": validade["dias_restantes"], "cnpj_confere_filial": self.cnpj_confere(),
            "possui_chave_privada": self.possui_chave_privada(),
        }
    
