"""
Extrai título e texto de uma matéria a partir da URL.

Necessário porque "List of All Alerts" só guarda Data/Veículo/URL — sem
título nem resumo. Para saber se a matéria é sobre a UFSB (e para alimentar
sentimento/categoria), é preciso abrir o link e ler o conteúdo.

Muitos links de 2021–2023 podem estar fora do ar. Isso é esperado: a
função sempre retorna um resultado (nunca lança exceção) para que o
pipeline continue processando as próximas linhas.
"""

import requests
from bs4 import BeautifulSoup

CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


def _extrair_com_trafilatura(html: str, url: str):
    try:
        import trafilatura
        texto = trafilatura.extract(html, url=url, include_comments=False)
        metadata = trafilatura.extract_metadata(html)
        titulo = metadata.title if metadata and metadata.title else None
        return titulo, texto
    except Exception:
        return None, None


def _extrair_com_beautifulsoup(html: str):
    soup = BeautifulSoup(html, "html.parser")
    titulo = None
    if soup.title and soup.title.string:
        titulo = soup.title.string.strip()
    elif soup.find("meta", property="og:title"):
        titulo = soup.find("meta", property="og:title").get("content", "").strip()

    paragrafos = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    texto = " ".join(paragrafos[:6])  # primeiros parágrafos bastam para sentimento/categoria
    return titulo, texto


def buscar_conteudo(url: str, timeout: int = 10) -> dict:
    """
    Retorna sempre um dict com as chaves: ok, titulo, texto, erro.
    Nunca lança exceção — falha de rede vira ok=False, para o pipeline seguir.
    """
    if not url or not url.startswith("http"):
        return {"ok": False, "titulo": "", "texto": "", "erro": "URL inválida ou vazia"}

    try:
        resposta = requests.get(url, headers=CABECALHOS, timeout=timeout, allow_redirects=True)
    except requests.exceptions.RequestException as exc:
        return {"ok": False, "titulo": "", "texto": "", "erro": f"Falha de conexão: {exc.__class__.__name__}"}

    if resposta.status_code >= 400:
        return {"ok": False, "titulo": "", "texto": "", "erro": f"HTTP {resposta.status_code}"}

    titulo, texto = _extrair_com_trafilatura(resposta.text, url)
    if not titulo and not texto:
        titulo, texto = _extrair_com_beautifulsoup(resposta.text)

    if not titulo:
        return {"ok": False, "titulo": "", "texto": "", "erro": "Não foi possível extrair título"}

    return {"ok": True, "titulo": titulo, "texto": texto or "", "erro": None}


if __name__ == "__main__":
    resultado = buscar_conteudo("https://exemplo-invalido-teste.xyz/materia")
    print(resultado)
