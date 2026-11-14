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

    # Fallback seguro para crescimento trimestral de lucro via quarterly_income_stmt se ausente no info
    if info.get("earningsQuarterlyGrowth") is None:
        try:
            q_stmt = ticker_obj.quarterly_income_stmt
            if q_stmt is not None and not q_stmt.empty:
                for row_label in ["Net Income", "Net Income Common Stockholders", "Operating Income"]:
                    if row_label in q_stmt.index:
                        series = q_stmt.loc[row_label].dropna()
                        if len(series) >= 2:
                            recent_val = float(series.iloc[0])
                            prev_val = float(series.iloc[1])
                            if prev_val != 0:
                                info["_calc_quarterly_growth"] = (recent_val - prev_val) / abs(prev_val)
                                break
        except Exception:
            pass
        
    return hist, info


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ibov_data(period: str) -> pd.DataFrame:
    """
    Busca os dados históricos do Ibovespa (^BVSP) com cache de 1 hora (3600s),
    evitando downloads repetidos a cada troca de ativo.
    """
    try:
        ibov_obj = yf.Ticker("^BVSP")
        yf_period = PERIOD_MAPPING.get(period, "6mo")
        hist = ibov_obj.history(period=yf_period, interval="1d")
        if hist is None or hist.empty:
            return pd.DataFrame()

        hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
        hist = hist[(hist['Open'] > 0) & (hist['High'] > 0) & (hist['Low'] > 0) & (hist['Close'] > 0)]
        return hist
    except Exception:
        return pd.DataFrame()


def calculate_canslim_metrics(hist_data: pd.DataFrame, ticker_info: dict, ibov_hist: pd.DataFrame) -> dict:
    """
    Avalia os 6 critérios quantitativos da metodologia CAN SLM adaptada para a B3:
    C - Current Earnings (Crescimento de Lucro Trimestral)
    A - Annual Earnings (ROE >= 15% e Lucro Positivo)
    N - New High (Preço até 15% abaixo da máxima de 52 semanas)
    S - Supply & Demand (Volume Relativo >= 1.2x em dia de alta)
    L - Leader or Laggard (Força Relativa superando o Ibovespa no período)
    M - Market Direction (Ibovespa acima da média móvel de 20 ou 50 períodos)
    Trata valores None ou NaN de forma segura como "N/D".
    """
    info = ticker_info if isinstance(ticker_info, dict) else {}
    criteria_details = []
    short_parts = []

    # --------------------------------------------------------------------------
    # C - Current Earnings (Crescimento Trimestral de Lucro > 15% ou positivo)
    # --------------------------------------------------------------------------
    q_growth = info.get("earningsQuarterlyGrowth")
    if q_growth is None or pd.isna(q_growth):
        q_growth = info.get("_calc_quarterly_growth")
    if q_growth is None or pd.isna(q_growth):
        q_growth = info.get("earningsGrowth")

    if q_growth is not None and not pd.isna(q_growth):
        try:
            q_pct = float(q_growth) * 100.0
            c_status = "approved" if q_pct > 15.0 or q_pct > 0.0 else "rejected"
            c_val = f"{q_pct:+.1f}%"
            c_desc = (
                "Crescimento trimestral forte (> 15%)."
                if q_pct >= 15.0
                else ("Crescimento trimestral positivo." if q_pct > 0 else "Retração no lucro trimestral.")
            )
            short_parts.append(f"Lucro Trim: {c_val}")
        except Exception:
            c_status, c_val, c_desc = "na", "N/D", "Dados trimestrais indisponíveis no Yahoo Finance."
            short_parts.append("Lucro Trim: N/D")
    else:
        c_status, c_val, c_desc = "na", "N/D", "Dados trimestrais indisponíveis para este ticker."
        short_parts.append("Lucro Trim: N/D")

    criteria_details.append({
        "letter": "C",
        "name": "Current Earnings (Lucro Trimestral)",
        "status": c_status,
        "value": c_val,
        "description": c_desc
    })

    # --------------------------------------------------------------------------
    # A - Annual Earnings (ROE >= 15% e lucro líquido anual positivo)
    # --------------------------------------------------------------------------
    roe = info.get("returnOnEquity")
    net_inc = info.get("netIncomeToCommon")
    profit_margin = info.get("profitMargins")
    trailing_eps = info.get("trailingEps")

    if roe is not None and not pd.isna(roe):
        try:
            roe_pct = float(roe) * 100.0
            # Verifica se o lucro líquido anual é positivo (quando disponível)
            lucro_positivo = True
            if net_inc is not None and not pd.isna(net_inc):
                lucro_positivo = float(net_inc) > 0
            elif profit_margin is not None and not pd.isna(profit_margin):
                lucro_positivo = float(profit_margin) > 0
            elif trailing_eps is not None and not pd.isna(trailing_eps):
                lucro_positivo = float(trailing_eps) > 0

            a_status = "approved" if (roe_pct >= 15.0 and lucro_positivo) else "rejected"
            a_val = f"ROE {roe_pct:.1f}%"
            a_desc = "Rentabilidade anual sólida (ROE >= 15% e lucro positivo)." if a_status == "approved" else "Abaixo da meta (exige ROE >= 15% e lucro positivo)."
            short_parts.append(f"ROE: {roe_pct:.1f}%")
        except Exception:
            a_status, a_val, a_desc = "na", "N/D", "Indicador ROE indisponível."
            short_parts.append("ROE: N/D")
    else:
        a_status, a_val, a_desc = "na", "N/D", "Indicador ROE anual indisponível para este ativo."
        short_parts.append("ROE: N/D")

    criteria_details.append({
        "letter": "A",
        "name": "Annual Earnings (Rentabilidade Anual)",
        "status": a_status,
        "value": a_val,
        "description": a_desc
    })

    # --------------------------------------------------------------------------
    # N - New High (Proximidade da máxima de 52 semanas: preço / 52wHigh >= 0.85)
    # --------------------------------------------------------------------------
    if hist_data is not None and not hist_data.empty:
        current_price = float(hist_data['Close'].iloc[-1])
        high_52w = info.get("fiftyTwoWeekHigh")
        if high_52w is None or pd.isna(high_52w) or float(high_52w) <= 0:
            high_52w = float(hist_data['High'].max())
        else:
            high_52w = max(float(high_52w), float(hist_data['High'].max()))

        if high_52w > 0:
            ratio_high = current_price / high_52w
            dist_high_pct = (ratio_high - 1.0) * 100.0
            n_status = "approved" if ratio_high >= 0.85 else "rejected"
            n_val = f"{dist_high_pct:+.1f}% (Topo: R$ {high_52w:.2f})"
            n_desc = "Negociando próximo à máxima de 52 semanas (até 15% do topo)." if n_status == "approved" else "Distante mais de 15% da máxima de 52 semanas."
            short_parts.append(f"Dist. Máx 52s: {dist_high_pct:+.1f}%")
        else:
            n_status, n_val, n_desc = "na", "N/D", "Máxima de 52 semanas indisponível."
            short_parts.append("Dist. Máx 52s: N/D")
    else:
        n_status, n_val, n_desc = "na", "N/D", "Histórico insuficiente."
        short_parts.append("Dist. Máx 52s: N/D")

    criteria_details.append({
        "letter": "N",
        "name": "New High (Proximidade do Topo 52s)",
        "status": n_status,
        "value": n_val,
        "description": n_desc
    })

    # --------------------------------------------------------------------------
    # S - Supply & Demand (Volume Relativo >= 1.2x com variação positiva de preço)
    # --------------------------------------------------------------------------
    if hist_data is not None and len(hist_data) >= 2 and 'Volume' in hist_data.columns:
        vol_current = float(hist_data['Volume'].iloc[-1])
        vol_avg_20d = float(hist_data['Volume'].tail(20).mean())
        close_curr = float(hist_data['Close'].iloc[-1])
        close_prev = float(hist_data['Close'].iloc[-2])
        price_change_pct = ((close_curr - close_prev) / close_prev) * 100.0 if close_prev > 0 else 0.0

        if vol_avg_20d > 0 and vol_current > 0:
            vol_rel = vol_current / vol_avg_20d
            s_status = "approved" if (vol_rel >= 1.2 and price_change_pct > 0) else "rejected"
            s_val = f"{vol_rel:.2f}x (Dia: {price_change_pct:+.2f}%)"
            s_desc = (
                "Forte demanda institucional (Volume >= 1.2x a média de 20d com alta no preço)."
                if s_status == "approved"
                else "Sem pico comprador (exige Volume >= 1.2x a média de 20d acompanhado de alta)."
            )
            short_parts.append(f"Vol. Rel: {vol_rel:.1f}x")
        else:
            s_status, s_val, s_desc = "na", "N/D", "Volume de negociação indisponível."
            short_parts.append("Vol. Rel: N/D")
    else:
        s_status, s_val, s_desc = "na", "N/D", "Dados de volume insuficientes."
        short_parts.append("Vol. Rel: N/D")

    criteria_details.append({
        "letter": "S",
        "name": "Supply & Demand (Oferta e Demanda)",
        "status": s_status,
        "value": s_val,
        "description": s_desc
    })

    # --------------------------------------------------------------------------
    # L - Leader or Laggard (Força Relativa vs ^BVSP no período selecionado)
    # --------------------------------------------------------------------------
    if hist_data is not None and len(hist_data) >= 2 and ibov_hist is not None and len(ibov_hist) >= 2:
        try:
            asset_start = float(hist_data['Close'].iloc[0])
            asset_end = float(hist_data['Close'].iloc[-1])
            ibov_start = float(ibov_hist['Close'].iloc[0])
            ibov_end = float(ibov_hist['Close'].iloc[-1])

            asset_ret_pct = ((asset_end / asset_start) - 1.0) * 100.0 if asset_start > 0 else 0.0
            ibov_ret_pct = ((ibov_end / ibov_start) - 1.0) * 100.0 if ibov_start > 0 else 0.0
            diff_ibov = asset_ret_pct - ibov_ret_pct

            l_status = "approved" if asset_ret_pct > ibov_ret_pct else "rejected"
            l_val = f"{diff_ibov:+.1f}% vs IBOV ({asset_ret_pct:+.1f}% vs {ibov_ret_pct:+.1f}%)"
            l_desc = (
                "Ativo líder: performance superior ao Ibovespa no período."
                if l_status == "approved"
                else "Performance abaixo do Ibovespa no período selecionado."
            )
            short_parts.append(f"vs IBOV: {diff_ibov:+.1f}%")
        except Exception:
            l_status, l_val, l_desc = "na", "N/D", "Não foi possível comparar com o Ibovespa."
            short_parts.append("vs IBOV: N/D")
    else:
        l_status, l_val, l_desc = "na", "N/D", "Dados do Ibovespa indisponíveis para comparação."
        short_parts.append("vs IBOV: N/D")

    criteria_details.append({
        "letter": "L",
        "name": "Leader or Laggard (Força Relativa vs IBOV)",
        "status": l_status,
        "value": l_val,
        "description": l_desc
    })

    # --------------------------------------------------------------------------
    # M - Market Direction (Tendência do Mercado: ^BVSP acima da MMA 20 ou 50)
    # --------------------------------------------------------------------------
    if ibov_hist is not None and not ibov_hist.empty and len(ibov_hist) >= 5:
        try:
            ibov_close = float(ibov_hist['Close'].iloc[-1])
            win_20 = min(20, len(ibov_hist))
            sma20_ibov = float(ibov_hist['Close'].rolling(window=win_20).mean().iloc[-1])

            if len(ibov_hist) >= 50:
                sma50_ibov = float(ibov_hist['Close'].rolling(window=50).mean().iloc[-1])
                above_ma = (ibov_close > sma20_ibov) or (ibov_close > sma50_ibov)
                ref_label = "MMA20/50"
            else:
                above_ma = ibov_close > sma20_ibov
                ref_label = f"MMA{win_20}"

            m_status = "approved" if above_ma else "rejected"
            m_trend_str = "Alta" if above_ma else "Pressão/Baixa"
            m_val = f"IBOV em {m_trend_str} ({ibov_close:,.0f} pts)"
            m_desc = (
                f"Direção favorável do mercado (^BVSP negociando acima da {ref_label})."
                if m_status == "approved"
                else f"Mercado em cautela/correção (^BVSP abaixo da {ref_label})."
            )
            short_parts.append(f"IBOV: {m_trend_str}")
        except Exception:
            m_status, m_val, m_desc = "na", "N/D", "Falha ao calcular tendência do Ibovespa."
            short_parts.append("IBOV: N/D")
    else:
        m_status, m_val, m_desc = "na", "N/D", "Dados históricos do ^BVSP indisponíveis."
        short_parts.append("IBOV: N/D")

    criteria_details.append({
        "letter": "M",
        "name": "Market Direction (Tendência do Mercado B3)",
        "status": m_status,
        "value": m_val,
        "description": m_desc
    })

    score = sum(1 for item in criteria_details if item["status"] == "approved")
    valid_criteria = sum(1 for item in criteria_details if item["status"] in ("approved", "rejected"))

    summary_line = f"CAN SLM ({score}/{valid_criteria}): " + " | ".join(short_parts)

    return {
        "score": score,
        "valid_criteria": valid_criteria,
        "criteria_details": criteria_details,
        "summary_line": summary_line
    }


def calculate_market_metrics(hist: pd.DataFrame, canslim_data: dict = None) -> dict:
    """
    Calcula métricas-chave de mercado a partir do histórico de cotações.
    Se canslim_data for fornecido, anexa o resumo CAN SLM à summary_line.
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

    base_summary = (
        f"Preço: R$ {current_price:.2f} | Var Dia: {daily_delta_pct:+.2f}% | "
        f"Var 5D: {var_5d:+.2f}% | MMA9: R$ {sma9_val:.2f} | MMA21: R$ {sma21_val:.2f}"
    )
    if canslim_data and canslim_data.get("summary_line"):
        base_summary = f"{base_summary} || {canslim_data['summary_line']}"

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
        "summary_line": base_summary
    }


@st.cache_data(ttl=900, show_spinner=False)
def scan_b3_market_opportunities(asset_list: list = None, scan_all: bool = True) -> list[dict]:
    """
    Escaneia os ativos populares da B3 identificando aqueles com tendência de alta,
    sinais técnicos de compra ou que estão em zonas interessantes para 'ficar de olho'.
    Por padrão escaneia a lista completa de ativos cadastrados em config.py (44 ativos).
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
        # Escaneia todos os 44 ativos ou o Top 20 conforme preferência
        asset_list = raw_list if scan_all else raw_list[:20]

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

