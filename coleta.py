"""
Etapa 1 — Coleta.

Junta notícias do Google News RSS (multi-consulta por campus/tema),
dos RSS de portais regionais cadastrados em config.py e, opcionalmente,
das menções/comentários da conta oficial do Instagram.

Cada registro coletado vira um dicionário com um formato único, para que
as etapas seguintes (tratamento, sentimento, categorização) não precisem
saber de onde a notícia veio.
"""

import time
import urllib.parse
from datetime import datetime, timezone

import feedparser
import requests

from config import TERMOS_BUSCA, JANELA_TEMPO, PORTAIS_RSS, ENABLE_INSTAGRAM, INSTAGRAM_BUSINESS_ACCOUNT_ID

HL, GL, CEID = "pt-BR", "BR", "BR:pt-419"


def montar_url_google_news(consulta: str) -> str:
    """Monta a URL de busca do Google News RSS para uma consulta específica."""
    query = f"{consulta} {JANELA_TEMPO}"
    q_encoded = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q_encoded}&hl={HL}&gl={GL}&ceid={CEID}"


def resolver_link_google_news(link_google: str) -> str:
    """
    Troca o link de redirecionamento do Google News pela URL real da matéria.
    Usa a biblioteca googlenewsdecoder; se falhar, mantém o link original
    (ele continua funcional para clique manual, só não é ideal para citação).
    """
    try:
        from googlenewsdecoder import new_decoderv1
        resultado = new_decoderv1(link_google, interval=1)
        if resultado.get("status"):
            return resultado["decoded_url"]
    except Exception:
        pass
    return link_google


def coletar_google_news() -> list[dict]:
    registros = []
    for grupo, consultas in TERMOS_BUSCA.items():
        for consulta in consultas:
            url_feed = montar_url_google_news(consulta)
            feed = feedparser.parse(url_feed)
            for entrada in feed.entries:
                link_real = resolver_link_google_news(entrada.link)
                registros.append({
                    "titulo": entrada.title,
                    "link": link_real,
                    "fonte": getattr(entrada, "source", {}).get("title", "Google News"),
                    "resumo": getattr(entrada, "summary", ""),
                    "data_publicacao": entrada.get("published", ""),
                    "grupo_busca": grupo,
                    "origem_coleta": "Google News RSS",
                })
            time.sleep(1)  # educado com o servidor entre consultas
    return registros


def coletar_portais_regionais() -> list[dict]:
    registros = []
    for portal in PORTAIS_RSS:
        feed = feedparser.parse(portal["url"])
        for entrada in feed.entries:
            registros.append({
                "titulo": entrada.title,
                "link": entrada.link,
                "fonte": portal["nome"],
                "resumo": getattr(entrada, "summary", ""),
                "data_publicacao": entrada.get("published", ""),
                "grupo_busca": "portal_regional",
                "origem_coleta": "RSS portal regional",
            })
    return registros


def coletar_instagram_oficial(access_token: str) -> list[dict]:
    """
    Cobre apenas a conta oficial da UFSB: publicações próprias e marcações
    onde a conta foi mencionada. É o único caminho gratuito e dentro dos
    termos de uso da Meta — não existe forma confiável de buscar menções
    públicas de terceiros sem token de app revisado pela Meta.
    """
    if not ENABLE_INSTAGRAM or not access_token:
        return []

    registros = []
    url = (
        f"https://graph.facebook.com/v20.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/tags"
        f"?fields=caption,permalink,timestamp,username&access_token={access_token}"
    )
    resp = requests.get(url, timeout=15)
    if resp.status_code == 200:
        for item in resp.json().get("data", []):
            registros.append({
                "titulo": (item.get("caption") or "")[:200],
                "link": item.get("permalink", ""),
                "fonte": f"Instagram (@{item.get('username', 'desconhecido')})",
                "resumo": item.get("caption", ""),
                "data_publicacao": item.get("timestamp", ""),
                "grupo_busca": "instagram_oficial",
                "origem_coleta": "Instagram Graph API",
            })
    return registros


def coletar_tudo(instagram_token: str | None = None) -> list[dict]:
    registros = []
    registros += coletar_google_news()
    registros += coletar_portais_regionais()
    if ENABLE_INSTAGRAM and instagram_token:
        registros += coletar_instagram_oficial(instagram_token)

    timestamp_coleta = datetime.now(timezone.utc).isoformat()
    for r in registros:
        r["coletado_em"] = timestamp_coleta
    return registros


if __name__ == "__main__":
    dados = coletar_tudo()
    print(f"{len(dados)} itens coletados.")
    for d in dados[:5]:
        print("-", d["titulo"], "|", d["fonte"])
