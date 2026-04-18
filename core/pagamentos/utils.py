def get_credencial(forma_pgto, chave):
    return (forma_pgto.credenciais or {}).get(chave)