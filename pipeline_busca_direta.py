"""
Pipeline de coleta direta — Google News RSS + Bing News RSS.

Roda junto com pipeline.py, nos mesmos horários (ver o workflow do
GitHub Actions). Reaproveita os mesmos módulos de limpeza, sentimento,
categorização e gravação usados pelo pipeline baseado em
"List of All Alerts" — a diferença é só a origem dos dados.

Como as duas fontes gravam no mesmo lugar ("clipping tratado") e a
gravação já deduplica por URL, não há risco de uma notícia encontrada
pelos dois caminhos (ex.: já processada de "List of All Alerts" e
também encontrada agora pelo Google News) entrar duplicada.
"""

import categorizacao
import coleta
import sentimento
import tratamento
from config import SHEET_ID, ABA_TRATADA
from planilha import anexar_ao_clipping_tratado


def montar_linha_clipping(registro: dict, sent: dict, cat: dict) -> dict:
    return {
        "Data": _formatar_data(registro.get("data_publicacao", "")),
        "Veículo": registro.get("fonte", ""),
        "Manchete": registro["titulo"],
        "Local": cat["local"],
        "URL": registro["link"],
        "viés (automático)": sent["sentimento"],
        "Tema": cat["tema"],
        "Campus": cat["campus"],
        "Origem": registro["origem_coleta"],
    }


def _formatar_data(data_rss: str) -> str:
    """RSS costuma vir em formato RFC 822 (ex.: 'Tue, 04 Nov 2025 10:00:00 GMT')."""
    if not data_rss:
        print("    aviso: item do RSS chegou sem data de publicação — Data ficará em branco.")
        return ""
    from dateutil import parser as date_parser
    try:
        return date_parser.parse(data_rss, fuzzy=True).strftime("%d/%m/%Y")
    except (ValueError, TypeError, OverflowError):
        print(f"    aviso: não reconheci a data '{data_rss}' vinda do RSS — Data ficará em branco.")
        return ""


def main():
    print("1/4 · Coletando via Google News e Bing News...")
    registros = coleta.coletar_tudo()
    print(f"    {len(registros)} itens encontrados nas buscas.")

    nao_resolvidos = sum(1 for r in registros if not r.get("link_resolvido", True))
    if nao_resolvidos:
        print(f"    aviso: {nao_resolvidos} item(ns) com link ainda não resolvido "
              f"(ficou apontando pro agregador) — serão ignorados para não gravar link errado.")

    print("2/4 · Limpando texto e filtrando por relevância...")
    candidatos = []
    vistos_nesta_execucao = set()
    for r in registros:
        if not r.get("link_resolvido", True):
            continue  # não arrisca gravar um link que não é o da matéria de verdade
        if r["link"] in vistos_nesta_execucao:
            continue  # mesma notícia encontrada em mais de uma consulta/fonte
        vistos_nesta_execucao.add(r["link"])

        titulo = tratamento.limpar_texto(r["titulo"])
        resumo = tratamento.limpar_texto(r.get("resumo", ""))
        if not categorizacao.eh_sobre_ufsb(f"{titulo} {resumo}"):
            continue
        candidatos.append({**r, "titulo": titulo, "resumo": resumo})

    print(f"    {len(candidatos)} candidato(s) relevante(s) após limpeza e checagem de relevância.")

    print("3/4 · Analisando sentimento e categoria...")
    linhas = []
    for r in candidatos:
        sent = sentimento.aplicar_uma(r["titulo"], r["resumo"])
        cat = categorizacao.categorizar(r["titulo"], r["resumo"])
        linhas.append(montar_linha_clipping(r, sent, cat))

    print(f"4/4 · Gravando em '{ABA_TRATADA}' (duplicatas por URL são ignoradas automaticamente)...")
    gravadas, urls_ja_existiam = anexar_ao_clipping_tratado(SHEET_ID, ABA_TRATADA, linhas)

    print(
        f"Concluído: {gravadas} nova(s) enviada(s) ao Clipping, "
        f"{len(urls_ja_existiam)} já existiam (encontradas por outra via)."
    )


if __name__ == "__main__":
    main()
