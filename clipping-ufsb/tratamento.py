"""
Etapa 2 — Tratamento e limpeza.

Recebe o DataFrame bruto (o que está na aba "Bruto" da planilha) e devolve
um DataFrame limpo: HTML removido, datas normalizadas, duplicatas exatas
e quase-duplicatas (mesma notícia replicada por veículos diferentes)
descartadas.
"""

import re
from difflib import SequenceMatcher

import pandas as pd
from dateutil import parser as date_parser

TAG_HTML = re.compile(r"<[^>]+>")
ESPACOS = re.compile(r"\s+")


def limpar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return ""
    texto = TAG_HTML.sub(" ", texto)
    texto = ESPACOS.sub(" ", texto)
    return texto.strip()


def normalizar_data(valor: str):
    if not valor:
        return pd.NaT
    try:
        return date_parser.parse(valor, fuzzy=True)
    except (ValueError, TypeError):
        return pd.NaT


def normalizar_url(url: str) -> str:
    if not isinstance(url, str):
        return ""
    url = url.split("?")[0].split("#")[0]
    return url.rstrip("/").lower()


def titulos_parecidos(a: str, b: str, limiar: float = 0.88) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= limiar


def remover_quase_duplicatas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove notícias com título quase idêntico publicadas na mesma janela de
    tempo (ex.: a mesma nota replicada por três portais parceiros).
    Mantém o primeiro registro encontrado de cada grupo.
    """
    manter = []
    titulos_mantidos = []
    for _, linha in df.iterrows():
        duplicado = any(titulos_parecidos(linha["titulo"], t) for t in titulos_mantidos)
        if not duplicado:
            manter.append(True)
            titulos_mantidos.append(linha["titulo"])
        else:
            manter.append(False)
    return df[manter]


def processar(df_bruto: pd.DataFrame) -> pd.DataFrame:
    df = df_bruto.copy()
    if df.empty:
        return df

    df["titulo"] = df["titulo"].apply(limpar_texto)
    df["resumo"] = df["resumo"].apply(limpar_texto)
    df["link_normalizado"] = df["link"].apply(normalizar_url)
    df["data_publicacao"] = df["data_publicacao"].apply(normalizar_data)

    df = df.dropna(subset=["titulo"])
    df = df[df["titulo"].str.len() > 0]

    # duplicata exata por URL normalizada
    df = df.drop_duplicates(subset=["link_normalizado"])

    # ordena por data para manter sempre a publicação mais antiga do grupo
    df = df.sort_values("data_publicacao", na_position="last")
    df = remover_quase_duplicatas(df)

    df = df.reset_index(drop=True)
    return df


if __name__ == "__main__":
    exemplo = pd.DataFrame([
        {"titulo": "UFSB lança <b>pesquisa</b> sobre restinga", "resumo": "...",
         "link": "https://site.com/materia?utm=x", "data_publicacao": "27 Jul 2026 10:00:00 GMT",
         "fonte": "Portal X", "grupo_busca": "reitoria_geral", "origem_coleta": "Google News RSS"},
        {"titulo": "UFSB lança pesquisa sobre restinga!", "resumo": "...",
         "link": "https://outrosite.com/materia2", "data_publicacao": "27 Jul 2026 11:00:00 GMT",
         "fonte": "Portal Y", "grupo_busca": "reitoria_geral", "origem_coleta": "Google News RSS"},
    ])
    resultado = processar(exemplo)
    print(resultado[["titulo", "fonte"]])
