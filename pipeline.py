"""
Pipeline do clipping digital UFSB — versão que processa o histórico real.

Fluxo, a cada execução (roda 3x/dia via GitHub Actions):
1. Lê até LOTE_MAXIMO_POR_EXECUCAO linhas pendentes de "List of All Alerts",
   da mais antiga para a mais nova.
2. Para cada uma: abre o link, extrai título/texto.
   - Link fora do ar / sem conteúdo → marca "Erro - link indisponível".
   - Conteúdo ok, mas não fala da UFSB → marca "Ignorado - não é sobre UFSB".
   - Conteúdo ok e fala da UFSB → sentimento + categoria, vira uma linha
     nova em "clipping tratado", e marca "OK - enviado ao Clipping".
3. Grava tudo em duas chamadas em lote: uma para o status na aba de
   origem, outra para as linhas novas em "clipping tratado" — preservando
   a ordem cronológica processada.
"""

import sys
import time

import categorizacao
import extrator
import sentimento
import tratamento
from config import (
    SHEET_ID, ABA_LEGADO_BRUTO, ABA_TRATADA, COLUNA_STATUS_BRUTO,
    LOTE_MAXIMO_POR_EXECUCAO, PAUSA_ENTRE_REQUISICOES_SEGUNDOS,
    TIMEOUT_REQUISICAO_SEGUNDOS,
)
from planilha import ler_pendentes_ordenados, marcar_status_em_lote, anexar_ao_clipping_tratado

STATUS_ERRO = "Erro - link indisponível"
STATUS_IGNORADO = "Ignorado - não é sobre UFSB"
STATUS_OK = "OK - enviado ao Clipping"
STATUS_JA_EXISTIA = "OK - já existia no Clipping"


def processar_um_item(item: dict):
    """Retorna (status_a_gravar, linha_para_clipping_ou_None)."""
    resultado = extrator.buscar_conteudo(item["url"], timeout=TIMEOUT_REQUISICAO_SEGUNDOS)
    if not resultado["ok"]:
        return STATUS_ERRO, None

    titulo = tratamento.limpar_texto(resultado["titulo"])
    texto = tratamento.limpar_texto(resultado["texto"])

    if not categorizacao.eh_sobre_ufsb(f"{titulo} {texto}"):
        return STATUS_IGNORADO, None

    sent = sentimento.aplicar_uma(titulo, texto)
    cat = categorizacao.categorizar(titulo, texto)

    data_fmt = item["data_hora"].strftime("%d/%m/%Y") if item["data_hora"] else ""
    linha_clipping = {
        "Data": data_fmt,
        "Veículo": item["veiculo"],
        "Manchete": titulo,
        "Local": cat["local"],
        "URL": item["url"],
        "viés (automático)": sent["sentimento"],
        "Tema": cat["tema"],
        "Campus": cat["campus"],
        "Origem": "Automático (processado de List of All Alerts)",
    }
    return STATUS_OK, linha_clipping


def main():
    print(f"Buscando até {LOTE_MAXIMO_POR_EXECUCAO} itens pendentes em '{ABA_LEGADO_BRUTO}'...")
    pendentes, coluna_status_numero = ler_pendentes_ordenados(
        SHEET_ID, ABA_LEGADO_BRUTO, COLUNA_STATUS_BRUTO, LOTE_MAXIMO_POR_EXECUCAO
    )
    print(f"{len(pendentes)} itens pendentes nesta execução.")

    if not pendentes:
        print("Nada para processar. Pipeline concluído.")
        return

    novas_linhas_clipping = []
    novos_status = {}
    linha_por_url = {}  # para corrigir o status depois de saber quais já existiam
    contagem = {"ok": 0, "ignorado": 0, "erro": 0}

    for n, item in enumerate(pendentes, start=1):
        status, linha = processar_um_item(item)
        novos_status[item["linha"]] = status

        if status == STATUS_OK:
            novas_linhas_clipping.append(linha)
            linha_por_url[linha["URL"]] = item["linha"]
            contagem["ok"] += 1
        elif status == STATUS_IGNORADO:
            contagem["ignorado"] += 1
        else:
            contagem["erro"] += 1

        if n % 25 == 0:
            print(f"  ... {n}/{len(pendentes)} processados")
        time.sleep(PAUSA_ENTRE_REQUISICOES_SEGUNDOS)

    print(f"Gravando {len(novas_linhas_clipping)} candidata(s) em '{ABA_TRATADA}'...")
    # remove duplicatas por URL dentro do próprio lote (ex.: o mesmo link
    # aparecendo em duas linhas antigas de "List of All Alerts")
    vistos_no_lote = set()
    linhas_sem_duplicata_interna = []
    for linha in novas_linhas_clipping:
        if linha["URL"] in vistos_no_lote:
            continue
        vistos_no_lote.add(linha["URL"])
        linhas_sem_duplicata_interna.append(linha)

    gravadas, urls_ja_existiam = anexar_ao_clipping_tratado(SHEET_ID, ABA_TRATADA, linhas_sem_duplicata_interna)

    # corrige o status das que já estavam no Clipping antes desta execução
    for url in urls_ja_existiam:
        linha_origem = linha_por_url.get(url)
        if linha_origem:
            novos_status[linha_origem] = STATUS_JA_EXISTIA

    print("Gravando status de volta em 'List of All Alerts' (1 chamada em lote)...")
    marcar_status_em_lote(SHEET_ID, ABA_LEGADO_BRUTO, coluna_status_numero, novos_status)

    print(
        f"Concluído: {gravadas} nova(s) enviada(s) ao Clipping, "
        f"{len(urls_ja_existiam)} já existiam no Clipping, "
        f"{contagem['ignorado']} ignoradas (não eram sobre UFSB), "
        f"{contagem['erro']} com link indisponível."
    )


if __name__ == "__main__":
    if SHEET_ID == "COLE_AQUI_O_ID_DA_PLANILHA":
        sys.exit("Configure o SHEET_ID em config.py antes de rodar o pipeline.")
    main()
