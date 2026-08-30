"""
Configuração central do clipping digital UFSB.
"""

# ---------------------------------------------------------------------------
# 1) PLANILHA GOOGLE SHEETS — a planilha real da ACS, alimentada desde 2021
# ---------------------------------------------------------------------------
SHEET_ID = "15QSgcDCIBxuKxpntClOf7krO75hyCMZstR6yD92Sv30"

# Fonte: a aba antiga (IFTTT/Zapier), alimentada automaticamente desde 2021.
# O pipeline LÊ dela, mas nunca apaga nem reordena o que já existe — só
# adiciona a coluna de status à direita.
ABA_LEGADO_BRUTO = "List of All Alerts"

# Destino: aba onde a equipe faz curadoria manual há anos.
ABA_TRATADA = "clipping tratado"

# Nova coluna adicionada em "List of All Alerts" para controlar o que já
# foi processado (evita reprocessar a mesma linha em toda execução).
COLUNA_STATUS_BRUTO = "Status do processamento"

# Quantas linhas pendentes processar POR EXECUÇÃO. Existem ~4 anos de
# histórico acumulado; processar tudo de uma vez estouraria o tempo do
# GitHub Actions. Com 3 execuções/dia, o histórico é varrido aos poucos,
# da mais antiga para a mais nova, sem perder o lugar entre execuções.
LOTE_MAXIMO_POR_EXECUCAO = 300

# Tempo máximo de espera por página ao abrir cada link, e pausa educada
# entre uma requisição e outra.
TIMEOUT_REQUISICAO_SEGUNDOS = 10
PAUSA_ENTRE_REQUISICOES_SEGUNDOS = 0.5

# ---------------------------------------------------------------------------
# 2) RELEVÂNCIA — o que conta como "é sobre a UFSB"
# ---------------------------------------------------------------------------
UFSB_KEYWORDS = [
    "UFSB",
    "Universidade Federal do Sul da Bahia",
    "Campus Sosígenes Costa",
    "Campus Jorge Amado",
    "Campus Paulo Freire",
]

# ---------------------------------------------------------------------------
# 3) CATEGORIZAÇÃO POR TEMA / CAMPUS / LOCAL (aplicada ao texto completo
#    extraído da matéria, não mais a um "grupo de busca")
# ---------------------------------------------------------------------------
TEMA_KEYWORDS = {
    "Economia do Mar": [
        "economia do mar", "oceanologia", "blue economy", "economia azul",
        "zona portuária", "porto marítimo", "marinha", "costeiro",
        "maricultura", "pesca artesanal", "amazônia azul",
    ],
    "Ciência e Pesquisa": [
        "pesquisa", "estudo", "cientista", "artigo científico", "descoberta",
        "El Niño", "monitoramento", "sensoriamento remoto",
    ],
    "Território e Sustentabilidade": [
        "mata atlântica", "restinga", "meio ambiente", "sustentabilidade",
        "preservação", "clima", "qualidade do ar", "floresta",
    ],
    "Ensino e Extensão": [
        "extensão universitária", "vestibular", "sisu", "enem", "matrícula",
        "curso", "graduação", "pós-graduação", "estudante",
    ],
    "Cultura, Gastronomia e Território": [
        "cacau", "chocolate", "gastronomia", "cultura", "território",
        "povos indígenas", "comunidade tradicional",
    ],
    "Gestão Institucional": [
        "reitor", "reitoria", "conselho universitário", "orçamento",
        "concurso", "edital", "convênio",
    ],
}

CAMPUS_KEYWORDS = {
    "Campus Sosígenes Costa (Porto Seguro)": ["porto seguro", "sosígenes costa", "sosigenes costa"],
    "Campus Jorge Amado (Itabuna/Ilhéus)": ["itabuna", "ilhéus", "ilheus", "jorge amado"],
    "Campus Paulo Freire (Teixeira de Freitas)": ["teixeira de freitas", "paulo freire"],
}

LOCAL_POR_CAMPUS = {
    "Campus Sosígenes Costa (Porto Seguro)": "Porto Seguro",
    "Campus Jorge Amado (Itabuna/Ilhéus)": "Itabuna/Ilhéus",
    "Campus Paulo Freire (Teixeira de Freitas)": "Teixeira de Freitas",
}
LOCAL_PADRAO = "BA"  # quando nenhum campus específico é identificado

MODELO_SENTIMENTO_LANG = "pt"

# ---------------------------------------------------------------------------
# 4) COLETA COMPLEMENTAR (OPCIONAL, desligada por padrão)
#    O pipeline principal agora usa "List of All Alerts" como fonte.
#    Esses parâmetros só importam se você decidir ligar coleta.py à parte.
# ---------------------------------------------------------------------------
TERMOS_BUSCA = {
    "campus_sosigenes_costa": ['"UFSB" "Porto Seguro"'],
    "campus_jorge_amado": ['"UFSB" "Itabuna"', '"UFSB" "Ilhéus"'],
    "campus_paulo_freire": ['"UFSB" "Teixeira de Freitas"'],
    "reitoria_geral": ['"Universidade Federal do Sul da Bahia"'],
}
JANELA_TEMPO = "when:2d"
PORTAIS_RSS = []
ENABLE_INSTAGRAM = False
INSTAGRAM_BUSINESS_ACCOUNT_ID = ""
