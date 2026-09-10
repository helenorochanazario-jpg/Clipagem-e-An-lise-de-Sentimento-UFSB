"""
Coleta direta — Google News RSS + Bing News RSS.

Diferente da "List of All Alerts" (que só guarda o que já aconteceu),
esta coleta busca ativamente por menções à UFSB nos dois maiores
agregadores de notícia gratuitos. As buscas já saem filtradas pelos
termos em config.py, mas o pipeline (pipeline_busca_direta.py) ainda
confere a relevância de novo antes de gravar, por segurança.

Os dois agregadores devolvem links de redirecionamento, não o link real
da matéria — por isso todo item passa por uma função de resolução antes
de sair daqui.
"""

import time
import urllib.parse
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, unquote

import feedparser
import requests

from config import TERMOS_BUSCA, JANELA_TEMPO, PORTAIS_RSS, ENABLE_INSTAGRAM, INSTAGRAM_BUSINESS_ACCOUNT_ID

HL, GL, CEID = "pt-BR", "BR", "BR:pt-419"
CABECALHOS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

DOMINIOS_AGREGADOR = ("news.google.com", "www.bing.com", "bing.com")


def _eh_link_de_agregador(url: str) -> bool:
    """True se o link ainda aponta para o próprio agregador (ou seja, a
    resolução falhou e o link NÃO é o da matéria de verdade)."""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return False
    return any(host == d or host.endswith("." + d) for d in DOMINIOS_AGREGADOR)


def _extrair_dominio(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except ValueError:
        return ""


# ---------------------------------------------------------------------------
# GOOGLE NEWS
# ---------------------------------------------------------------------------

def montar_url_google_news(consulta: str) -> str:
    query = f"{consulta} {JANELA_TEMPO}"
    q_encoded = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q_encoded}&hl={HL}&gl={GL}&ceid={CEID}"


def resolver_link_google_news(link_google: str) -> str:
    """
    O link do Google News não é um redirecionamento HTTP comum — é um
    token que só a própria Google consegue decodificar. Por isso usamos
    a biblioteca googlenewsdecoder (que faz essa consulta por baixo dos
    panos). Se falhar, mantém o link original como último recurso.
    """
    try:
        from googlenewsdecoder import new_decoderv1
        resultado = new_decoderv1(link_google, interval=1)
        if resultado.get("status") and resultado.get("decoded_url"):
            return resultado["decoded_url"]
    except Exception:
        pass
    return link_google


def coletar_google_news() -> list[dict]:
    registros = []
    for grupo, consultas in TERMOS_BUSCA.items():
        for consulta in consultas:
            feed = feedparser.parse(montar_url_google_news(consulta))
            for entrada in feed.entries:
                link_real = resolver_link_google_news(entrada.link)
                registros.append({
                    "titulo": entrada.title,
                    "link": link_real,
                    "link_resolvido": not _eh_link_de_agregador(link_real),
                    "fonte": getattr(entrada, "source", {}).get("title", "") or _extrair_dominio(link_real),
                    "resumo": getattr(entrada, "summary", ""),
                    "data_publicacao": entrada.get("published") or entrada.get("updated") or entrada.get("pubDate") or "",
                    "grupo_busca": grupo,
                    "origem_coleta": "Automático (Google News RSS)",
                })
            time.sleep(1)  # educado com o servidor entre consultas
    return registros


# ---------------------------------------------------------------------------
# BING NEWS
# ---------------------------------------------------------------------------

def montar_url_bing_news(consulta: str) -> str:
    q_encoded = urllib.parse.quote(consulta)
    return f"https://www.bing.com/news/search?q={q_encoded}&format=rss&setmkt=pt-BR"


def resolver_link_bing(link_bing: str) -> str:
    """
    Links do Bing News costumam vir como
    bing.com/news/apiclick.aspx?...&url=URL_CODIFICADA&...
    Primeiro tenta ler a URL real direto do parâmetro "url" (mais rápido,
    sem chamada de rede extra); se não achar, segue o redirecionamento
    HTTP de verdade e usa a URL final da resposta.

    Aviso: não consegui testar esta função contra o bing.com de verdade
    no ambiente em que este código foi escrito (rede bloqueada para esse
    domínio). A lógica segue o padrão documentado do Bing, mas vale
    conferir o resultado real na primeira execução (ver README).
    """
    try:
        partes = urlparse(link_bing)
        query = parse_qs(partes.query)
        for chave in ("url", "u"):
            if chave in query and query[chave]:
                candidato = unquote(query[chave][0])
                if candidato.startswith("http") and not _eh_link_de_agregador(candidato):
                    return candidato
    except ValueError:
        pass

    try:
        resposta = requests.get(link_bing, headers=CABECALHOS, timeout=10, allow_redirects=True)
        if resposta.url and not _eh_link_de_agregador(resposta.url):
            return resposta.url
    except requests.exceptions.RequestException:
        pass

    return link_bing  # não resolveu; mantém o original (marcado como não resolvido)


def coletar_bing_news() -> list[dict]:
    registros = []
    for grupo, consultas in TERMOS_BUSCA.items():
        for consulta in consultas:
            feed = feedparser.parse(montar_url_bing_news(consulta))
            for entrada in feed.entries:
                link_real = resolver_link_bing(entrada.link)
                registros.append({
                    "titulo": entrada.title,
                    "link": link_real,
                    "link_resolvido": not _eh_link_de_agregador(link_real),
                    "fonte": getattr(entrada, "source", {}).get("title", "") or _extrair_dominio(link_real),
                    "resumo": getattr(entrada, "summary", ""),
                    "data_publicacao": entrada.get("published") or entrada.get("updated") or entrada.get("pubDate") or "",
                    "grupo_busca": grupo,
                    "origem_coleta": "Automático (Bing News RSS)",
                })
            time.sleep(1)
    return registros


# ---------------------------------------------------------------------------
# PORTAIS REGIONAIS (RSS próprio) E INSTAGRAM — inalterados
# ---------------------------------------------------------------------------

def coletar_portais_regionais() -> list[dict]:
    registros = []
    for portal in PORTAIS_RSS:
        feed = feedparser.parse(portal["url"])
        for entrada in feed.entries:
            registros.append({
                "titulo": entrada.title,
                "link": entrada.link,
                "link_resolvido": True,
                "fonte": portal["nome"],
                "resumo": getattr(entrada, "summary", ""),
                "data_publicacao": entrada.get("published") or entrada.get("updated") or entrada.get("pubDate") or "",
                "grupo_busca": "portal_regional",
                "origem_coleta": "Automático (RSS portal regional)",
            })
    return registros


def coletar_instagram_oficial(access_token: str) -> list[dict]:
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
                "link_resolvido": True,
                "fonte": f"Instagram (@{item.get('username', 'desconhecido')})",
                "resumo": item.get("caption", ""),
                "data_publicacao": item.get("timestamp", ""),
                "grupo_busca": "instagram_oficial",
                "origem_coleta": "Automático (Instagram Graph API)",
            })
    return registros


def coletar_tudo(instagram_token: str | None = None) -> list[dict]:
    registros = []
    registros += coletar_google_news()
    registros += coletar_bing_news()
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
    nao_resolvidos = [d for d in dados if not d["link_resolvido"]]
    print(f"{len(nao_resolvidos)} com link não resolvido (ainda aponta pro agregador).")
    for d in dados[:5]:
        print("-", d["origem_coleta"], "|", d["titulo"], "|", d["link"])
