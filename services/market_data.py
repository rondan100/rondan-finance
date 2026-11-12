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
    Aplica filtros rigorosos de sanitização para evitar glitches (ex: candles zerados à noite).
    """
    ticker_obj = yf.Ticker(symbol)
    yf_period = PERIOD_MAPPING.get(period, "6mo")
    
    hist = ticker_obj.history(period=yf_period, interval="1d")
    
    if hist.empty:
        return None, {}

    # 1. Limpeza de linhas nulas ou zeradas (muito comum em consultas noturnas ou after-market)
    hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
    hist = hist[(hist['Open'] > 0) & (hist['High'] > 0) & (hist['Low'] > 0) & (hist['Close'] > 0)]

    # 2. Correção de anomalias pontuais onde o Low cai artificialmente para 0 ou valor absurdo
    if not hist.empty:
        # Garante que Low não seja menor que 50% do mínimo entre Open e Close (evita pavio falso até zero)
        min_body = hist[['Open', 'Close']].min(axis=1)
        glitch_mask = hist['Low'] < (min_body * 0.5)
        if glitch_mask.any():
            hist.loc[glitch_mask, 'Low'] = min_body[glitch_mask]

    # 3. Se a última linha ainda tiver Low zerado ou volume 0 e corpo inconsistente, descarta o candle incompleto
    if len(hist) > 1:
        last_row = hist.iloc[-1]
        if last_row['Low'] <= 0 or last_row['Close'] <= 0:
            hist = hist.iloc[:-1]
        
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


@st.cache_data(ttl=900, show_spinner=False)
def scan_b3_market_opportunities(asset_list: list = None) -> list[dict]:
    """
    Escaneia os ativos mais populares da B3 identificando aqueles com tendência de alta,
    sinais técnicos de compra ou que estão em zonas interessantes para 'ficar de olho'.
    Cache de 15 minutos (900s) para garantir agilidade e performance.
    """
    from config import PopularB3Asset

    if asset_list is None:
        # Extrai os tickers das ações populares (excluindo a opção OUTRO)
        raw_list = [
            asset.value.split(" - ")[0].strip()
            for asset in PopularB3Asset
            if asset != PopularB3Asset.OUTRO
        ]
        # Pega as 16 principais para um escaneamento rápido e equilibrado
        asset_list = raw_list[:16]

    results = []

    for ticker in asset_list:
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="3mo", interval="1d")

            if hist.empty or len(hist) < 22:
                continue

            # Sanitização contra zeros/glitches
            hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
            hist = hist[(hist['Open'] > 0) & (hist['High'] > 0) & (hist['Low'] > 0) & (hist['Close'] > 0)]

            if len(hist) < 22:
                continue

            hist['SMA9'] = hist['Close'].rolling(window=9).mean()
            hist['SMA21'] = hist['Close'].rolling(window=21).mean()

            last = hist.iloc[-1]
            prev = hist.iloc[-2]

            price = last['Close']
            sma9 = last['SMA9']
            sma21 = last['SMA21']
            prev_price = prev['Close']
            daily_pct = ((price - prev_price) / prev_price) * 100 if prev_price else 0.0

            # Variação 5 dias
            if len(hist) >= 6:
                c5 = hist['Close'].iloc[-6]
                var5d = ((price - c5) / c5) * 100
            else:
                var5d = daily_pct

            # Variação 1 mês (~21 pregões)
            c21 = hist['Close'].iloc[-21]
            var21d = ((price - c21) / c21) * 100

            # Nome da empresa
            company = B3_ASSET_NAMES.get(ticker.replace(".SA", ""), ticker.replace(".SA", ""))

            # Classificação Técnica do Ativo
            # 1. Compra Forte: Preço acima das duas médias e MMA9 acima de MMA21 em expansão
            if price > sma9 > sma21 and var5d > 0:
                sinal = "🟢 Compra Forte"
                categoria = "COMPRA"
                score = 95 + min(var5d, 10)
                motivo = "Preço em alta acima das MMAs 9 e 21 com fluxo comprador forte."

            # 2. Tendência de Alta: Preço e MMA9 sustentados acima da MMA21
            elif price > sma21 and sma9 > sma21:
                sinal = "🟢 Tendência de Alta"
                categoria = "COMPRA"
                score = 80 + min(var5d, 10)
                motivo = "Tendência compradora estabelecida com suporte na MMA 21."

            # 3. Interessante ficar de olho: Rompendo MMA21 ou cruzamento recente MMA9 x MMA21
            elif (price > sma21 and prev['Close'] <= sma21) or (sma9 > sma21 and prev['SMA9'] <= prev['SMA21']) or (price > sma9 and var5d > 1.5):
                sinal = "🟡 Ficar de Olho"
                categoria = "OLHO"
                score = 70 + min(var5d, 10)
                motivo = "Movimento de reversão ou rompimento altista das médias móveis."

            # 4. Em consolidação / neutro
            elif abs(price - sma21) / sma21 < 0.015:
                sinal = "⚪ Neutro / Lateral"
                categoria = "NEUTRO"
                score = 50
                motivo = "Ativo testando região de médias, aguardando definição de tendência."

            # 5. Baixa
            else:
                sinal = "🔴 Baixa / Correção"
                categoria = "BAIXA"
                score = 30 + max(var5d, -20)
                motivo = "Preço negociando abaixo das médias móveis de curto e médio prazo."

            results.append({
                "ticker": ticker,
                "company": company,
                "price": price,
                "daily_pct": daily_pct,
                "var5d": var5d,
                "var21d": var21d,
                "sma9": sma9,
                "sma21": sma21,
                "sinal": sinal,
                "categoria": categoria,
                "score": score,
                "motivo": motivo
            })

        except Exception:
            continue

    # Ordenar por score decrescente (as melhores oportunidades de compra no topo)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

