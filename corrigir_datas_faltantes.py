"""
Corrige retroativamente linhas em "clipping tratado" que ficaram com a
coluna "Data" em branco (efeito do bug de parsing já corrigido em
planilha.py — datas com dia > 12, tipo "17/06/2021", quebravam o parser
antigo em silêncio).

Estratégia, por linha sem Data:
1. Se a URL também existir em "List of All Alerts", usa a "Date & Time"
   de lá (agora lida com o parser corrigido).
2. Senão (veio de Google News/Bing, ou a URL não bate com nada em
   "List of All Alerts"), reabre a página e tenta extrair a data de
   publicação dos metadados da própria matéria.
3. O que não for possível resolver automaticamente fica listado no
   final, para revisão manual.

Nunca reescreve nenhuma outra coluna — só preenche células de "Data"
que estavam vazias.

Uso:
    python corrigir_datas_faltantes.py
"""

import sys

import requests
import trafilatura
from dateutil import parser as date_parser

import extrator
from config import SHEET_ID, ABA_TRATADA, ABA_LEGADO_BRUTO
from planilha import abrir_aba, marcar_status_em_lote, parse_data_hora_legado


def montar_indice_list_of_all_alerts() -> dict:
    """URL -> texto original de 'Date & Time', lido uma única vez."""
    aba = abrir_aba(SHEET_ID, ABA_LEGADO_BRUTO)
    valores = aba.get_all_values()
    cabecalho = valores[0]
    idx_data = cabecalho.index("Date & Time")
    idx_url = cabecalho.index("URL")

    indice = {}
    for linha in valores[1:]:
        if idx_url < len(linha) and linha[idx_url].strip():
            indice[linha[idx_url].strip()] = linha[idx_data] if idx_data < len(linha) else ""
    return indice


def tentar_extrair_data_da_pagina(url: str):
    """Reabre a matéria e tenta ler a data de publicação dos metadados
    da própria página (a maioria dos sites de notícia expõe isso)."""
    try:
        resposta = requests.get(url, headers=extrator.CABECALHOS, timeout=10)
        if resposta.status_code >= 400:
            return None
        metadata = trafilatura.extract_metadata(resposta.text)
        if metadata and metadata.date:
            return date_parser.parse(metadata.date, fuzzy=True)
    except Exception:
        pass
    return None


def main():
    print(f"Lendo '{ABA_TRATADA}' em busca de linhas com Data em branco...")
    aba = abrir_aba(SHEET_ID, ABA_TRATADA)
    valores = aba.get_all_values()
    cabecalho = valores[0]

    for coluna_obrigatoria in ("Data", "URL", "Origem"):
        if coluna_obrigatoria not in cabecalho:
            sys.exit(f"A aba '{ABA_TRATADA}' não tem a coluna '{coluna_obrigatoria}' esperada.")

    idx_data = cabecalho.index("Data")
    idx_url = cabecalho.index("URL")

    pendentes = []
    for i, linha in enumerate(valores[1:], start=2):
        data_atual = linha[idx_data] if idx_data < len(linha) else ""
        url = linha[idx_url] if idx_url < len(linha) else ""
        if not data_atual.strip() and url.strip():
            pendentes.append({"linha": i, "url": url.strip()})

    print(f"{len(pendentes)} linha(s) com Data em branco e URL preenchida.")
    if not pendentes:
        print("Nada para corrigir.")
        return

    print("Carregando índice de 'List of All Alerts' para cruzar por URL (1 leitura só)...")
    indice_legado = montar_indice_list_of_all_alerts()

    correcoes = {}
    nao_resolvidas = []

    for n, item in enumerate(pendentes, start=1):
        data_hora = None

        if item["url"] in indice_legado:
            data_hora = parse_data_hora_legado(indice_legado[item["url"]])

        if not data_hora:
            data_hora = tentar_extrair_data_da_pagina(item["url"])

        if data_hora:
            correcoes[item["linha"]] = data_hora.strftime("%d/%m/%Y")
        else:
            nao_resolvidas.append(item["url"])

        if n % 25 == 0:
            print(f"  ... {n}/{len(pendentes)} verificadas")

    print(f"\n{len(correcoes)} corrigida(s) automaticamente.")
    if correcoes:
        marcar_status_em_lote(SHEET_ID, ABA_TRATADA, idx_data + 1, correcoes)
        print("Gravado em uma única chamada em lote.")

    if nao_resolvidas:
        print(f"\n{len(nao_resolvidas)} não foi possível resolver automaticamente "
              f"(link fora do ar, sem metadado de data, ou não achei em 'List of All Alerts'). "
              f"Revisar manualmente:")
        for url in nao_resolvidas:
            print(" -", url)


if __name__ == "__main__":
    if SHEET_ID == "COLE_AQUI_O_ID_DA_PLANILHA":
        sys.exit("Configure o SHEET_ID em config.py antes de rodar este script.")
    main()
