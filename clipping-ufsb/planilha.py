"""
Módulo de acesso à planilha real da ACS (Google Sheets via gspread).

Regra de ouro: nunca reescreve nem reordena colunas existentes. Colunas
novas são sempre adicionadas ao final do cabeçalho.

Todas as operações em lote (leitura e escrita) usam o mínimo de chamadas
à API do Google Sheets possível, para não esbarrar em limite de cota
quando há centenas de linhas pendentes.
"""

import json
import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

ESCOPO = ["https://www.googleapis.com/auth/spreadsheets"]

COLUNAS_CLIPPING_TRATADO = [
    "Data", "Veículo", "Manchete", "Local", "viés",   # já existiam
    "URL", "viés (automático)", "Tema", "Campus", "Origem",  # novas
]


def conectar() -> gspread.Client:
    credencial_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if credencial_json:
        info = json.loads(credencial_json)
        creds = Credentials.from_service_account_info(info, scopes=ESCOPO)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=ESCOPO)
    return gspread.authorize(creds)


def abrir_aba(sheet_id: str, nome_aba: str):
    cliente = conectar()
    planilha = cliente.open_by_key(sheet_id)
    return planilha.worksheet(nome_aba)


def garantir_colunas(aba, colunas_desejadas: list[str]) -> list[str]:
    cabecalho = aba.row_values(1)
    faltantes = [c for c in colunas_desejadas if c not in cabecalho]
    for coluna in faltantes:
        aba.update_cell(1, len(cabecalho) + 1, coluna)
        cabecalho.append(coluna)
    return cabecalho


def _parse_data_hora(valor: str):
    formatos = ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y")
    for fmt in formatos:
        try:
            return datetime.strptime(valor.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def ler_pendentes_ordenados(sheet_id: str, aba_bruto_nome: str, coluna_status: str, limite: int):
    """
    Lê "List of All Alerts", garante que a coluna de status existe, e
    devolve até `limite` linhas com status vazio, ordenadas da mais
    antiga para a mais nova pela coluna "Date & Time".

    Cada item devolvido inclui o número da linha real na planilha
    (para depois marcar o status exatamente naquela linha).
    """
    aba = abrir_aba(sheet_id, aba_bruto_nome)
    cabecalho = garantir_colunas(aba, [coluna_status])
    todas_as_linhas = aba.get_all_values()[1:]  # pula cabeçalho

    idx_data = cabecalho.index("Date & Time")
    idx_publisher = cabecalho.index("Publisher")
    idx_url = cabecalho.index("URL")
    idx_status = cabecalho.index(coluna_status)

    pendentes = []
    for i, linha in enumerate(todas_as_linhas, start=2):  # linha 1 é cabeçalho
        status_atual = linha[idx_status] if idx_status < len(linha) else ""
        if status_atual.strip():
            continue  # já processada
        data_hora_texto = linha[idx_data] if idx_data < len(linha) else ""
        data_hora = _parse_data_hora(data_hora_texto)
        pendentes.append({
            "linha": i,
            "data_hora": data_hora,
            "data_hora_texto": data_hora_texto,
            "veiculo": linha[idx_publisher] if idx_publisher < len(linha) else "",
            "url": linha[idx_url] if idx_url < len(linha) else "",
        })

    # mais antigas primeiro; quem não tem data reconhecível vai para o final
    pendentes.sort(key=lambda r: r["data_hora"] or datetime.max)
    return pendentes[:limite], (idx_status + 1)  # +1: gspread usa colunas 1-indexadas


def marcar_status_em_lote(sheet_id: str, aba_bruto_nome: str, coluna_status_numero: int, atualizacoes: dict):
    """
    atualizacoes: {numero_da_linha: "texto do status"}
    Escreve tudo em UMA chamada à API (batch_update), em vez de uma
    chamada por linha — essencial para não estourar cota processando
    lotes de centenas de itens.
    """
    if not atualizacoes:
        return
    aba = abrir_aba(sheet_id, aba_bruto_nome)
    letra_coluna = gspread.utils.rowcol_to_a1(1, coluna_status_numero).rstrip("1")
    corpo = [
        {"range": f"{letra_coluna}{linha}", "values": [[status]]}
        for linha, status in atualizacoes.items()
    ]
    aba.batch_update(corpo, value_input_option="USER_ENTERED")


def urls_existentes_no_clipping(aba, cabecalho: list[str]) -> set:
    if "URL" not in cabecalho:
        return set()
    col_index = cabecalho.index("URL") + 1
    valores = aba.col_values(col_index)[1:]
    return {v.strip() for v in valores if v.strip()}


def anexar_ao_clipping_tratado(sheet_id: str, nome_aba: str, registros: list[dict]):
    """
    Anexa, em uma única chamada, as linhas cuja URL ainda não existe em
    "clipping tratado" (a coluna "viés" nunca é preenchida aqui).

    Retorna (quantidade_gravada, urls_ja_existentes) — o segundo item
    permite ao pipeline corrigir o status na aba de origem para os casos
    em que a notícia já estava no Clipping antes desta execução.
    """
    if not registros:
        return 0, set()

    aba = abrir_aba(sheet_id, nome_aba)
    cabecalho = garantir_colunas(aba, COLUNAS_CLIPPING_TRATADO)
    ja_existentes = urls_existentes_no_clipping(aba, cabecalho)

    novos = [r for r in registros if r.get("URL") not in ja_existentes]
    urls_puladas = {r.get("URL") for r in registros if r.get("URL") in ja_existentes}

    if novos:
        linhas = [[str(r.get(coluna, "")) for coluna in cabecalho] for r in novos]
        aba.append_rows(linhas, value_input_option="USER_ENTERED")

    return len(novos), urls_puladas
