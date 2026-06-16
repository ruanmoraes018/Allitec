import crcmod
import qrcode
import os
import io
import base64

class Payload():
    def __init__(self, nome, chavepix, valor, cidade, txtId, descricao='', diretorio=''):
        self.nome = nome
        self.chavepix = chavepix
        self.valor = valor.replace(',', '.')
        self.cidade = cidade
        self.txtId = txtId
        self.descricao = descricao
        self.diretorioQrCode = diretorio
        self.nome_tam = len(self.nome)
        self.chavepix_tam = len(self.chavepix)
        self.valor_tam = len(self.valor)
        self.cidade_tam = len(self.cidade)
        self.txtId_tam = len(self.txtId)
        self.gui = 'BR.GOV.BCB.PIX'
        self.merchantAccount_tam = (
            f'00{len(self.gui):02}{self.gui}'
            f'01{self.chavepix_tam:02}{self.chavepix}'
        )
        if self.descricao:
            descricao_tam = len(self.descricao)
            self.merchantAccount_tam += (
                f'02{descricao_tam:02}{self.descricao}'
            )
        self.transactionAmount_tam = f'{self.valor_tam:02}{float(self.valor):.2f}'
        self.addDataField_tam = f'05{self.txtId_tam:02}{self.txtId}'
        self.nome_tam = f'{self.nome_tam:02}'
        self.cidade_tam = f'{self.cidade_tam:02}'
        self.payloadFormat = '000201'
        self.merchantAccount = f'26{len(self.merchantAccount_tam):02}{self.merchantAccount_tam}'
        self.merchantCategCode = '52040000'
        self.transactionCurrency = '5303986'
        self.transactionAmount = f'54{self.transactionAmount_tam}'
        self.countryCode = '5802BR'
        self.merchantName = f'59{self.nome_tam:02}{self.nome}'
        self.merchantCity = f'60{self.cidade_tam:02}{self.cidade}'
        self.addDataField = f'62{len(self.addDataField_tam):02}{self.addDataField_tam}'
        self.crc16 = '6304'

    def gerarPayload(self):

        self.payload = f'{self.payloadFormat}{self.merchantAccount}{self.merchantCategCode}{self.transactionCurrency}{self.transactionAmount}{self.countryCode}{self.merchantName}{self.merchantCity}{self.addDataField}{self.crc16}'
        return self.gerarCrc16(self.payload)

    def gerarCrc16(self, payload):

        crc16 = crcmod.mkCrcFun(poly=0x11021, initCrc=0xFFFF, rev=False, xorOut=0x0000)

        self.crc16Code = hex(crc16(str(payload).encode('utf-8')))

        self.crc16Code_formatado = str(self.crc16Code).replace('0x', '').upper().zfill(4)

        self.payload_completa = f'{payload}{self.crc16Code_formatado}'

        return self.gerarQrCode(self.payload_completa, self.diretorioQrCode)

    def gerarQrCode(self, payload, diretorio=None):

        img = qrcode.make(payload)

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')

        qr_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode()

        return {
            'payload': payload,
            'qr_code': qr_base64
        }

if __name__ == '__main__':
    Payload('RUAN MORAES DE ASSUNCAO', '+5591982817656', '120.00', 'CAPITAO POCO', 'TESTE', diretorio='pixqrcodegen/').gerarPayload()
