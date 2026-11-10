"""
Módulo de coleta e processamento de dados de mercado (B3 via yfinance).
"""

import re
import pandas as pd
import streamlit as st
import yfinance as yf
from config import PERIOD_MAPPING, B3_ASSET_NAMES, CACHE_TTL_MARKET_DATA


def normalize_ticker(symbol: str) -> str:
    """
    Normaliza o código do ticker, adicionando .SA para ativos da B3 caso necessário.
    """
    s = symbol.strip().upper()
    if not s:
        return "PETR4.SA"
    if not s.endswith(".SA") and "." not in s and "^" not in s:
        return f"{s}.SA"
    return s


def get_search_name(symbol: str, ticker_info: dict) -> str:
    """
    Obtém o nome amigável da empresa para busca de notícias no Google News.
    Prioriza o mapeamento B3 e faz fallback para o shortName da empresa.
    """
    clean_sym = symbol.replace(".SA", "").upper()
    if clean_sym in B3_ASSET_NAMES:
        return B3_ASSET_NAMES[clean_sym]
    
    short_name = ticker_info.get("shortName") or ticker_info.get("longName")
    if short_name:
        # Remover sufixos societários comuns como S/A, ON, PN, LTDA, etc.
        cleaned = re.sub(r'\b(ON|PN|EJ|ED|EB|N1|N2|NM|S\.?A\.?|LTDA)\b', '', short_name, flags=re.IGNORECASE).strip()
        if len(cleaned) > 2:
            return cleaned
            
    return clean_sym


@st.cache_data(ttl=CACHE_TTL_MARKET_DATA, show_spinner=False)
def fetch_stock_data(symbol: str, period: str):
    """
    Busca cotações e histórico OHLC via yfinance com cache configurado.
    Calcula médias móveis simples de 9 e 21 períodos.
    """
    ticker_obj = yf.Ticker(symbol)
    yf_period = PERIOD_MAPPING.get(period, "6mo")
    
    hist = ticker_obj.history(period=yf_period, interval="1d")
    
    if hist.empty:
        return None, {}
        
    # Calcular Médias Móveis Simples (MMA 9 e MMA 21)
    hist['SMA9'] = hist['Close'].rolling(window=9).mean()
    hist['SMA21'] = hist['Close'].rolling(window=21).mean()
    
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}
        
    return hist, info


def calculate_market_metrics(hist: pd.DataFrame) -> dict:
    """
    Calcula métricas-chave de mercado a partir do histórico de cotações.
    """
    latest_row = hist.iloc[-1]
    current_price = latest_row['Close']

    if len(hist) > 1:
        previous_close = hist.iloc[-2]['Close']
    else:
        previous_close = latest_row['Open']

    daily_delta_val = current_price - previous_close
    daily_delta_pct = (daily_delta_val / previous_close) * 100 if previous_close else 0.0

    sma9_val = latest_row['SMA9'] if pd.notna(latest_row['SMA9']) else current_price
    sma21_val = latest_row['SMA21'] if pd.notna(latest_row['SMA21']) else current_price
    max_period = hist['High'].max()
    min_period = hist['Low'].min()

    # Variação acumulada dos últimos 5 pregões
    if len(hist) >= 5:
        close_5d = hist['Close'].iloc[-5]
        var_5d = ((current_price - close_5d) / close_5d) * 100
    else:
        var_5d = daily_delta_pct

    return {
        "current_price": current_price,
        "previous_close": previous_close,
        "daily_delta_val": daily_delta_val,
        "daily_delta_pct": daily_delta_pct,
        "sma9_val": sma9_val,
        "sma21_val": sma21_val,
        "max_period": max_period,
        "min_period": min_period,
        "var_5d": var_5d,
        "summary_line": (
            f"Preço: R$ {current_price:.2f} | Var Dia: {daily_delta_pct:+.2f}% | "
            f"Var 5D: {var_5d:+.2f}% | MMA9: R$ {sma9_val:.2f} | MMA21: R$ {sma21_val:.2f}"
        )
    }

