"""
Etapa de categorização e checagem de relevância.

Tudo aqui trabalha em cima do texto completo extraído da matéria
(título + corpo), não mais de um "grupo de busca" pré-definido — porque
agora a fonte é a "List of All Alerts", que não vem organizada por campus.
"""

import re

from config import TEMA_KEYWORDS, CAMPUS_KEYWORDS, LOCAL_POR_CAMPUS, LOCAL_PADRAO, UFSB_KEYWORDS


def _contem_palavra(texto_lower: str, palavra: str) -> bool:
    """Casa por palavra/expressão inteira (\\b) — evita falso positivo
    tipo 'porto' bater dentro de 'Porto Seguro'."""
    padrao = r"\b" + re.escape(palavra.lower()) + r"\b"
    return re.search(padrao, texto_lower) is not None


def eh_sobre_ufsb(texto: str) -> bool:
    """Critério de relevância: menção direta à UFSB ou a algum dos seus campi."""
    texto_lower = (texto or "").lower()
    return any(_contem_palavra(texto_lower, termo) for termo in UFSB_KEYWORDS)


def _todas_correspondencias(texto_lower: str, dicionario_categorias: dict) -> list[str]:
    return [cat for cat, palavras in dicionario_categorias.items() if any(_contem_palavra(texto_lower, p) for p in palavras)]


def _primeira_correspondencia(texto_lower: str, dicionario_categorias: dict) -> str:
    encontradas = _todas_correspondencias(texto_lower, dicionario_categorias)
    return encontradas[0] if encontradas else "Não classificado"


def categorizar(titulo: str, texto: str) -> dict:
    completo = f"{titulo or ''} {texto or ''}"
    texto_lower = completo.lower()

    tema = _primeira_correspondencia(texto_lower, TEMA_KEYWORDS)
    campi_encontrados = _todas_correspondencias(texto_lower, CAMPUS_KEYWORDS)

    if len(campi_encontrados) == 1:
        campus = campi_encontrados[0]
        local = LOCAL_POR_CAMPUS.get(campus, LOCAL_PADRAO)
    else:
        # zero campi citados OU mais de um (matéria genuinamente multicampi)
        campus = "Multicampi / Reitoria"
        local = LOCAL_PADRAO

    return {"campus": campus, "tema": tema, "local": local}


if __name__ == "__main__":
    exemplos = [
        ("UFSB oferece mais de 1.600 vagas em Ilhéus, Porto Seguro e Teixeira de Freitas", ""),
        ("Prefeitura de Eunápolis anuncia obras no centro", "Nada sobre universidade aqui."),
        ("UFSB e pesquisadores discutem economia do mar em seminário", ""),
    ]
    for titulo, texto in exemplos:
        print(titulo, "-> relevante:", eh_sobre_ufsb(f"{titulo} {texto}"), "|", categorizar(titulo, texto))
