"""
Configurações Globais e Constantes do Dashboard Financeiro B3.
"""

from enum import Enum


class PopularB3Asset(str, Enum):
    """
    Enumeração das ações mais populares e negociadas na B3.
    """
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
    JBSS3 = "JBSS3.SA - JBS (ON)"
    B3SA3 = "B3SA3.SA - B3 Bolsa Balcão (ON)"
    GGBR4 = "GGBR4.SA - Gerdau (PN)"
    CSNA3 = "CSNA3.SA - CSN Siderúrgica (ON)"
    EMBR3 = "EMBR3.SA - Embraer (ON)"
    ELET3 = "ELET3.SA - Eletrobras (ON)"
    RADL3 = "RADL3.SA - Raia Drogasil (ON)"
    VIVT3 = "VIVT3.SA - Telefônica Vivo (ON)"
    RAIZ4 = "RAIZ4.SA - Raízen (PN)"
    EQTL3 = "EQTL3.SA - Equatorial Energia (ON)"
    LREN3 = "LREN3.SA - Lojas Renner (ON)"
    CMIN3 = "CMIN3.SA - CSN Mineração (ON)"
    ASAI3 = "ASAI3.SA - Assaí Atacadista (ON)"
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
    "PETR4": "Petrobras",
    "PETR3": "Petrobras",
    "VALE3": "Vale",
    "ITUB4": "Itaú Unibanco",
    "BBDC4": "Bradesco",
    "BBAS3": "Banco do Brasil",
    "ABEV3": "Ambev",
    "MGLU3": "Magazine Luiza",
    "WEGE3": "WEG",
    "RENT3": "Localiza",
    "SUZB3": "Suzano",
    "JBSS3": "JBS",
    "B3SA3": "B3 Bolsa Balcão",
    "GGBR4": "Gerdau",
    "CSNA3": "CSN Siderúrgica",
    "EMBR3": "Embraer",
    "ELET3": "Eletrobras",
    "ELET6": "Eletrobras",
    "PRIO3": "PRIO Petróleo",
    "HAPV3": "Hapvida",
    "RADL3": "Raia Drogasil",
    "VIVT3": "Telefônica Brasil Vivo",
    "RAIZ4": "Raízen",
    "CPLE6": "Copel",
    "EQTL3": "Equatorial Energia",
    "LREN3": "Lojas Renner",
    "AZUL4": "Azul Linhas Aéreas",
    "GOLL4": "Gol Linhas Aéreas",
    "CMIN3": "CSN Mineração",
    "UGPA3": "Ultrapar",
    "ASAI3": "Assaí Atacadista",
    "CRFB3": "Carrefour Brasil"
}

