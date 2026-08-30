"""
Teste de simulação do pipeline — roda a lógica inteira (relevância,
sentimento, categorização, ordenação, status, deduplicação) sem acessar
a internet nem a planilha real. Útil para conferir rapidamente o
comportamento depois de editar `config.py` ou qualquer outro módulo.

Uso:
    python testar_simulacao.py
"""

from datetime import datetime
from unittest import mock

# ---- Dataset simulado de "List of All Alerts" ----
# Propositalmente fora de ordem cronológica, para testar a reordenação.
PENDENTES_SIMULADOS = [
    {"linha": 5, "data_hora": datetime(2021, 6, 20), "data_hora_texto": "6/20/2021", "veiculo": "G1", "url": "https://site.com/materia-irrelevante"},
    {"linha": 2, "data_hora": datetime(2021, 6, 17), "data_hora_texto": "6/17/2021", "veiculo": "G1", "url": "https://site.com/materia-ufsb-antiga"},
    {"linha": 9, "data_hora": datetime(2025, 11, 4), "data_hora_texto": "11/4/2025", "veiculo": "Boca News", "url": "https://site.com/materia-ufsb-recente"},
    {"linha": 11, "data_hora": None, "data_hora_texto": "", "veiculo": "Portal X", "url": "https://site.com/link-quebrado"},
    {"linha": 3, "data_hora": datetime(2021, 6, 17), "data_hora_texto": "6/17/2021", "veiculo": "G1", "url": "https://site.com/ja-existe-no-clipping"},
]

CONTEUDO_FALSO = {
    "https://site.com/materia-irrelevante": {"ok": True, "titulo": "Idosa é encontrada morta no sul da Bahia", "texto": "Polícia investiga o caso.", "erro": None},
    "https://site.com/materia-ufsb-antiga": {"ok": True, "titulo": "UFSB abre inscrições em Porto Seguro", "texto": "Universidade Federal do Sul da Bahia abre vagas.", "erro": None},
    "https://site.com/materia-ufsb-recente": {"ok": True, "titulo": "UFSB oferece vagas em Ilhéus, Porto Seguro e Teixeira de Freitas", "texto": "Universidade abre inscrições em três campi.", "erro": None},
    "https://site.com/link-quebrado": {"ok": False, "titulo": "", "texto": "", "erro": "HTTP 404"},
    "https://site.com/ja-existe-no-clipping": {"ok": True, "titulo": "UFSB é destaque em pesquisa sobre restinga", "texto": "Estudo premiado.", "erro": None},
}


def fake_buscar_conteudo(url, timeout=10):
    return CONTEUDO_FALSO[url]


def fake_ler_pendentes_ordenados(sheet_id, aba, coluna_status, limite):
    ordenados = sorted(PENDENTES_SIMULADOS, key=lambda r: r["data_hora"] or datetime.max)
    return ordenados[:limite], 4


status_gravados = {}


def fake_marcar_status_em_lote(sheet_id, aba, coluna_status_numero, atualizacoes):
    status_gravados.update(atualizacoes)


linhas_gravadas_clipping = []


def fake_anexar_ao_clipping_tratado(sheet_id, aba, registros):
    # simula 1 duplicata já existente no Clipping antes desta execução
    ja_existente_url = "https://site.com/materia-ufsb-antiga"
    novos = [r for r in registros if r["URL"] != ja_existente_url]
    puladas = {r["URL"] for r in registros if r["URL"] == ja_existente_url}
    linhas_gravadas_clipping.extend(novos)
    return len(novos), puladas


def fake_sentimento_aplicar_uma(titulo, texto):
    # evita baixar o modelo pysentimiento (pesado) só para testar o encaixe da lógica
    texto_l = (titulo + texto).lower()
    if "destaque" in texto_l or "premiado" in texto_l:
        return {"sentimento": "positivo", "confianca": 0.9}
    return {"sentimento": "neutro", "confianca": 0.5}


def rodar():
    with mock.patch("extrator.buscar_conteudo", side_effect=fake_buscar_conteudo), \
         mock.patch("planilha.ler_pendentes_ordenados", side_effect=fake_ler_pendentes_ordenados), \
         mock.patch("planilha.marcar_status_em_lote", side_effect=fake_marcar_status_em_lote), \
         mock.patch("planilha.anexar_ao_clipping_tratado", side_effect=fake_anexar_ao_clipping_tratado), \
         mock.patch("sentimento.aplicar_uma", side_effect=fake_sentimento_aplicar_uma):

        import config
        config.SHEET_ID = "sheet-de-teste"
        import pipeline
        pipeline.main()

    print("\n--- STATUS QUE SERIAM GRAVADOS EM 'List of All Alerts' ---")
    for linha, status in sorted(status_gravados.items()):
        print(f"  linha {linha}: {status}")

    print("\n--- LINHAS QUE SERIAM GRAVADAS EM 'clipping tratado' (nesta ordem) ---")
    for l in linhas_gravadas_clipping:
        print(f"  {l['Data']} | {l['Veículo']} | {l['Manchete']} | Campus={l['Campus']} | Tema={l['Tema']} | viés(auto)={l['viés (automático)']}")


if __name__ == "__main__":
    rodar()
