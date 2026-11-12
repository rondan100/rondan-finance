"""
Configurações Globais e Constantes do Dashboard Financeiro B3.
"""

from enum import Enum


class PopularB3Asset(str, Enum):
    """
    Enumeração das ações, units e BDRs mais populares e negociados na B3.
    """
    # Lista original (com tickers atualizados)
    PETR4 = "PETR4.SA - Petrobras (PN)"
    VALE3 = "VALE3.SA - Vale (ON)"
    ITUB4 = "ITUB4.SA - Itaú Unibanco (PN)"
    BBDC4 = "BBDC4.SA - Bradesco (PN)"
    BBAS3 = "BBAS3.SA - Banco do Brasil (ON)"
    WEGE3 = "WEGE3.SA - WEG (ON)"
    PRIO3 = "PRIO3.SA - PRIO Petróleo (ON)"
    ABEV3 = "ABEV3.SA - Ambev (ON)"
    MGLU3 = "MGLU3.SA - Magazine Luiza (ON)"
    RENT3 = "RENT3.SA - Localiza (ON)"
    SUZB3 = "SUZB3.SA - Suzano (ON)"
    JBSS32 = "JBSS32.SA - JBS (BDR)"
    B3SA3 = "B3SA3.SA - B3 Bolsa Balcão (ON)"
    GGBR4 = "GGBR4.SA - Gerdau (PN)"
    CSNA3 = "CSNA3.SA - CSN Siderúrgica (ON)"
    EMBJ3 = "EMBJ3.SA - Embraer (ON)"
    AXIA3 = "AXIA3.SA - Axia Energia / ex-Eletrobras (ON)"
    RADL3 = "RADL3.SA - RD Saúde / Raia Drogasil (ON)"
    VIVT3 = "VIVT3.SA - Telefônica Vivo (ON)"
    RAIZ4 = "RAIZ4.SA - Raízen (PN)"
    EQTL3 = "EQTL3.SA - Equatorial Energia (ON)"
    LREN3 = "LREN3.SA - Lojas Renner (ON)"
    CMIN3 = "CMIN3.SA - CSN Mineração (ON)"
    ASAI3 = "ASAI3.SA - Assaí Atacadista (ON)"

    # +20 tickers populares adicionados
    PETR3 = "PETR3.SA - Petrobras (ON)"
    ITSA4 = "ITSA4.SA - Itaúsa (PN)"
    BPAC11 = "BPAC11.SA - BTG Pactual (Unit)"
    SANB11 = "SANB11.SA - Santander Brasil (Unit)"
    SBSP3 = "SBSP3.SA - Sabesp (ON)"
    CMIG4 = "CMIG4.SA - Cemig (PN)"
    CPLE3 = "CPLE3.SA - Copel (ON)"
    TAEE11 = "TAEE11.SA - Taesa (Unit)"
    EGIE3 = "EGIE3.SA - Engie Brasil (ON)"
    VBBR3 = "VBBR3.SA - Vibra Energia (ON)"
    UGPA3 = "UGPA3.SA - Ultrapar (ON)"
    CSAN3 = "CSAN3.SA - Cosan (ON)"
    RAIL3 = "RAIL3.SA - Rumo Logística (ON)"
    KLBN11 = "KLBN11.SA - Klabin (Unit)"
    RDOR3 = "RDOR3.SA - Rede D'Or (ON)"
    HAPV3 = "HAPV3.SA - Hapvida (ON)"
    TOTS3 = "TOTS3.SA - TOTVS (ON)"
    TIMS3 = "TIMS3.SA - TIM Brasil (ON)"
    MULT3 = "MULT3.SA - Multiplan (ON)"
    BRAV3 = "BRAV3.SA - Brava Energia (ON)"

    # Opção manual
    OUTRO = "OUTRO - Digitar código personalizado"


# Configurações do Ativo Padrão
DEFAULT_TICKER = "PETR4.SA"
DEFAULT_PERIOD = "6m"

# Mapeamento de períodos amigáveis para formato aceito pelo yfinance
PERIOD_MAPPING = {
    "1m": "1mo",
    "3m": "3mo",
    "6m": "6mo",
    "1y": "1y"
}

# Modelos disponíveis por ordem de prioridade.
# gemini-3.5-flash-lite: 500 req/dia (padrão) — NÃO suporta thinking_config
# gemini-3.8-flash:      20 req/dia (fallback) — suporta thinking_config
# gemini-3.6-flash:      20 req/dia (fallback) — suporta thinking_config
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
]

# Cota diária gratuita de cada modelo (RPD — Requests Per Day no Google AI Studio)
GEMINI_MODEL_RPD = {
    "gemini-3.5-flash-lite": 500,
    "gemini-3.8-flash":       20,
    "gemini-3.6-flash":       20,
}

# Tempos de expiração de cache (TTL em segundos)
CACHE_TTL_MARKET_DATA = 300   # 5 minutos
CACHE_TTL_NEWS = 300          # 5 minutos
CACHE_TTL_AI = 1800           # 30 minutos

# Quantidade de notícias a buscar e a enviar no prompt
MAX_NEWS_TO_DISPLAY = 8
MAX_NEWS_FOR_PROMPT = 5

# Dicionário de Nomes Populares da B3 para busca no Google News
B3_ASSET_NAMES = {
    # Ativos principais e atualizados
    "PETR4": "Petrobras",
    "PETR3": "Petrobras",
    "VALE3": "Vale mineradora",
    "ITUB4": "Itaú Unibanco",
    "BBDC4": "Bradesco",
    "BBAS3": "Banco do Brasil",
    "WEGE3": "WEG",
    "PRIO3": "PRIO Petróleo",
    "ABEV3": "Ambev",
    "MGLU3": "Magazine Luiza",
    "RENT3": "Localiza veículos",
    "SUZB3": "Suzano",
    "JBSS32": "JBS",
    "B3SA3": "B3 Bolsa Balcão",
    "GGBR4": "Gerdau",
    "CSNA3": "CSN Siderúrgica",
    "EMBJ3": "Embraer",
    "AXIA3": "Axia Energia",
    "RADL3": "RD Saúde",
    "VIVT3": "Telefônica Brasil Vivo",
    "RAIZ4": "Raízen",
    "EQTL3": "Equatorial Energia",
    "LREN3": "Lojas Renner",
    "CMIN3": "CSN Mineração",
    "ASAI3": "Assaí Atacadista",

    # Novos ativos adicionados (+20)
    "ITSA4": "Itaúsa",
    "BPAC11": "BTG Pactual",
    "SANB11": "Santander Brasil",
    "SBSP3": "Sabesp",
    "CMIG4": "Cemig",
    "CPLE3": "Copel",
    "TAEE11": "Taesa",
    "EGIE3": "Engie Brasil",
    "VBBR3": "Vibra Energia",
    "UGPA3": "Ultrapar",
    "CSAN3": "Cosan",
    "RAIL3": "Rumo Logística",
    "KLBN11": "Klabin",
    "RDOR3": "Rede D'Or",
    "HAPV3": "Hapvida",
    "TOTS3": "TOTVS",
    "TIMS3": "TIM Brasil",
    "MULT3": "Multiplan",
    "BRAV3": "Brava Energia",

    # Extras mantidos para busca personalizada (OUTRO)
    "CPLE6": "Copel",
    "AZUL4": "Azul Linhas Aéreas",
    "GOLL4": "Gol Linhas Aéreas",
    "CRFB3": "Carrefour Brasil",
}
