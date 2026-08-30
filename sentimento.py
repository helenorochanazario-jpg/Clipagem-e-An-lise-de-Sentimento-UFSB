"""
Etapa 3 — Análise de sentimento.

Usa o pysentimiento (modelo BERTimbau afinado para português) para
classificar cada notícia em POS / NEU / NEG, com o score de confiança
de cada classe. O modelo é baixado uma vez (na primeira execução) e
fica em cache local — em GitHub Actions isso acontece a cada execução
a menos que se configure cache de dependências.
"""

_analisador = None


def _carregar_analisador():
    global _analisador
    if _analisador is None:
        from pysentimiento import create_analyzer
        _analisador = create_analyzer(task="sentiment", lang="pt")
    return _analisador


# minúsculo de propósito: mesmo padrão da coluna "viés" já usada pela equipe
ROTULO_PT = {"POS": "positivo", "NEU": "neutro", "NEG": "negativo"}


def analisar_texto(texto: str) -> dict:
    if not texto:
        return {"sentimento": "neutro", "confianca": 0.0}
    analisador = _carregar_analisador()
    # o modelo tem limite de tokens: truncamos para o parágrafo inicial
    resultado = analisador.predict(texto[:512])
    rotulo_bruto = resultado.output  # "POS" | "NEU" | "NEG"
    confianca = resultado.probas[rotulo_bruto]
    return {"sentimento": ROTULO_PT[rotulo_bruto], "confianca": round(confianca, 3)}


def aplicar_uma(titulo: str, texto: str) -> dict:
    """Recebe título + texto extraído da matéria e devolve o sentimento
    já traduzido (positivo/neutro/negativo)."""
    completo = f"{titulo or ''}. {(texto or '')[:400]}"
    return analisar_texto(completo)


if __name__ == "__main__":
    for titulo, texto in [
        ("UFSB é destaque nacional em pesquisa sobre restinga", "Estudo é elogiado por especialistas."),
        ("Alunos denunciam falta de estrutura em campus da UFSB", "Situação preocupa comunidade acadêmica."),
    ]:
        print(titulo, "->", aplicar_uma(titulo, texto))
