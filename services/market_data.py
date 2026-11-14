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

    # Fallback seguro para crescimento trimestral YoY (C) e CAGR anual 3-4 anos + ROE (A)
    try:
        q_stmt = ticker_obj.quarterly_income_stmt
        if q_stmt is not None and not q_stmt.empty:
            for row_label in ["Diluted EPS", "Basic EPS", "Net Income", "Net Income Common Stockholders"]:
                if row_label in q_stmt.index:
                    series = q_stmt.loc[row_label].dropna()
                    # Coluna 0 (trimestre mais recente) vs Coluna 4 (mesmo trimestre do ano anterior - YoY)
                    if len(series) >= 5:
                        recent_val = float(series.iloc[0])
                        yoy_prev_val = float(series.iloc[4])
                        if yoy_prev_val > 0:
                            info["_calc_quarterly_yoy_growth"] = (recent_val - yoy_prev_val) / yoy_prev_val
                            break
                        elif yoy_prev_val < 0 and recent_val > 0:
                            # Reversão de prejuízo para lucro YoY
                            info["_calc_quarterly_yoy_growth"] = (recent_val - yoy_prev_val) / abs(yoy_prev_val)
                            break
                        elif yoy_prev_val < 0 and recent_val <= 0:
                            info["_calc_quarterly_yoy_negative"] = True
                            break
    except Exception:
        pass

    try:
        a_stmt = ticker_obj.income_stmt
        if a_stmt is not None and not a_stmt.empty:
            for row_label in ["Net Income", "Net Income Common Stockholders", "Diluted EPS", "Basic EPS"]:
                if row_label in a_stmt.index:
                    series = a_stmt.loc[row_label].dropna()
                    if len(series) >= 2:
                        # Limita aos últimos 4 intervalos anuais disponíveis (3 a 4 anos no yfinance)
                        series_window = series.iloc[:5]
                        anos = len(series_window) - 1
                        lucro_recente = float(series_window.iloc[0])
                        lucro_antigo = float(series_window.iloc[-1])
                        info["_calc_cagr_years"] = int(anos)
                        if lucro_recente > 0 and lucro_antigo > 0 and anos >= 1:
                            cagr_val = (lucro_recente / lucro_antigo) ** (1.0 / anos) - 1.0
                            info["_calc_annual_cagr"] = float(cagr_val)
                        else:
                            info["_calc_annual_cagr_nonpositive"] = True
                            info["_calc_recent_profit_positive"] = bool(lucro_recente > 0)
                        break
    except Exception:
        pass
        
    return hist, info


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ibov_data(period: str = "2y") -> pd.DataFrame:
    """
    Busca os dados históricos do Ibovespa (^BVSP) com cache de 1 hora (3600s).
    Baixa sempre period='2y' (~500 pregões) independentemente do período selecionado
    no gráfico pelo usuário, garantindo dados suficientes para calcular MM50 e MM200 sem NaN.
    """
    try:
        ibov_obj = yf.Ticker("^BVSP")
        hist = ibov_obj.history(period="2y", interval="1d")
        if hist is None or hist.empty:
            return pd.DataFrame()

        hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
        hist = hist[(hist['Open'] > 0) & (hist['High'] > 0) & (hist['Low'] > 0) & (hist['Close'] > 0)]
        return hist
    except Exception:
        return pd.DataFrame()


def calculate_canslim_metrics(hist_data: pd.DataFrame, ticker_info: dict, ibov_hist: pd.DataFrame) -> dict:
    """
    Avalia os critérios quantitativos da metodologia CAN SLM adaptada para a B3:
    M - Market Direction (Peso Principal via ^BVSP: MM50 e MM200 em 3 estados: ALTA, ATENCAO, BAIXA)
    C - Current Earnings (Crescimento Trimestral YoY > 20%)
    A - Annual Earnings (CAGR Anual > 25% em 3-4 anos + ROE >= 17%)
    N - New High (Preço até 15% abaixo da máxima de 52 semanas)
    S - Supply & Demand (Volume Relativo >= 1.2x em dia de alta)
    L - Leader or Laggard (Força Relativa superando o Ibovespa no período selecionado)
    Trata valores None ou NaN de forma segura como "N/D".
    """
    info = ticker_info if isinstance(ticker_info, dict) else {}
    criteria_details = []
    short_parts = []

    # --------------------------------------------------------------------------
    # C - Current Earnings (Lucro Trimestral YoY > 20%)
    # --------------------------------------------------------------------------
    q_yoy = info.get("earningsQuarterlyGrowth")
    if q_yoy is None or pd.isna(q_yoy):
        q_yoy = info.get("_calc_quarterly_yoy_growth")

    if q_yoy is not None and not pd.isna(q_yoy):
        try:
            q_pct = float(q_yoy) * 100.0
            c_status = "approved" if q_yoy > 0.20 else "rejected"
            c_val = f"YoY {q_pct:+.1f}%"
            c_desc = (
                f"Aprovado: Lucro/LPA trimestral cresceu {q_pct:+.1f}% YoY (meta > 20%)."
                if c_status == "approved"
                else f"Abaixo da meta: Lucro/LPA trimestral em {q_pct:+.1f}% YoY (exige > 20%)."
            )
            short_parts.append(f"LPA YoY: {q_pct:+.1f}%")
        except Exception:
            c_status, c_val, c_desc = "na", "N/D", "Dados de LPA trimestral YoY indisponíveis."
            short_parts.append("LPA YoY: N/D")
    elif info.get("_calc_quarterly_yoy_negative"):
        c_status = "rejected"
        c_val = "Prejuízo Trim."
        c_desc = "Resultado trimestral negativo (prejuízo no trimestre atual e/ou anterior)."
        short_parts.append("LPA YoY: Prejuízo")
    else:
        c_status, c_val, c_desc = "na", "N/D", "Dados de lucro trimestral YoY indisponíveis para este ticker."
        short_parts.append("LPA YoY: N/D")

    criteria_details.append({
        "letter": "C",
        "name": "Current Earnings (Lucro Trimestral YoY > 20%)",
        "status": c_status,
        "value": c_val,
        "description": c_desc
    })

    # --------------------------------------------------------------------------
    # A - Annual Earnings (CAGR > 25% em 3-4 anos + ROE >= 17%)
    # --------------------------------------------------------------------------
    cagr_anual = info.get("_calc_annual_cagr")
    cagr_years = info.get("_calc_cagr_years", 3)
    cagr_nonpositive = info.get("_calc_annual_cagr_nonpositive", False)
    roe = info.get("returnOnEquity")

    has_cagr = cagr_anual is not None and not pd.isna(cagr_anual)
    has_roe = roe is not None and not pd.isna(roe)

    if has_cagr or has_roe or cagr_nonpositive:
        try:
            cagr_pct = float(cagr_anual) * 100.0 if has_cagr else None
            roe_pct = float(roe) * 100.0 if has_roe else None

            if cagr_nonpositive:
                a_status = "rejected"
                roe_str = f" | ROE {roe_pct:.1f}%" if roe_pct is not None else ""
                a_val = f"CAGR N/A (Prejuízo){roe_str}"
                a_desc = "Balanço anual registra prejuízo no período base ou recente (exige CAGR > 25% e ROE >= 17%)."
                short_parts.append(f"CAGR Anual: Prejuízo ({f'ROE {roe_pct:.0f}%' if roe_pct is not None else 'ROE N/D'})")
            elif has_cagr and has_roe:
                is_approved = (float(cagr_anual) > 0.25) and (float(roe) >= 0.17)
                a_status = "approved" if is_approved else "rejected"
                a_val = f"CAGR {cagr_pct:+.1f}% ({cagr_years}a) | ROE {roe_pct:.1f}%"
                a_desc = (
                    f"Aprovado: CAGR anual de {cagr_pct:+.1f}% (> 25%) e ROE de {roe_pct:.1f}% (>= 17%)."
                    if is_approved
                    else f"Abaixo da meta: exige CAGR anual > 25% (atual {cagr_pct:+.1f}%) e ROE >= 17% (atual {roe_pct:.1f}%)."
                )
                short_parts.append(f"CAGR Anual: {cagr_pct:+.1f}% (ROE {roe_pct:.0f}%)")
            elif has_cagr and not has_roe:
                if float(cagr_anual) <= 0.25:
                    a_status = "rejected"
                    a_val = f"CAGR {cagr_pct:+.1f}% ({cagr_years}a) | ROE N/D"
                    a_desc = f"CAGR anual de {cagr_pct:+.1f}% abaixo da meta de 25% (ROE indisponível)."
                else:
                    a_status = "na"
                    a_val = f"CAGR {cagr_pct:+.1f}% ({cagr_years}a) | ROE N/D"
                    a_desc = f"CAGR anual atende (> 25%), mas ROE indisponível no Yahoo Finance (meta >= 17%)."
                short_parts.append(f"CAGR Anual: {cagr_pct:+.1f}% (ROE N/D)")
            else:
                # Apenas ROE disponível
                if float(roe) < 0.17:
                    a_status = "rejected"
                    a_val = f"CAGR N/D | ROE {roe_pct:.1f}%"
                    a_desc = f"ROE de {roe_pct:.1f}% abaixo da meta mínima de 17% (CAGR anual indisponível)."
                else:
                    a_status = "na"
                    a_val = f"CAGR N/D | ROE {roe_pct:.1f}%"
                    a_desc = f"ROE de {roe_pct:.1f}% atende (>= 17%), mas histórico de balanços p/ CAGR indisponível."
                short_parts.append(f"CAGR Anual: N/D (ROE {roe_pct:.0f}%)")
        except Exception:
            a_status, a_val, a_desc = "na", "N/D", "Falha ao calcular CAGR anual e ROE."
            short_parts.append("CAGR Anual: N/D")
    else:
        a_status, a_val, a_desc = "na", "N/D", "Histórico anual de lucros e ROE indisponíveis para este ativo."
        short_parts.append("CAGR Anual: N/D")

    criteria_details.append({
        "letter": "A",
        "name": "Annual Earnings (CAGR > 25% + ROE >= 17%)",
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
            n_desc = (
                "Negociando próximo à máxima de 52 semanas (até 15% abaixo do topo)."
                if n_status == "approved"
                else "Distante mais de 15% da máxima de 52 semanas."
            )
            short_parts.append(f"Dist. Máx 52s: {dist_high_pct:+.1f}%")
        else:
            n_status, n_val, n_desc = "na", "N/D", "Máxima de 52 semanas indisponível."
            short_parts.append("Dist. Máx 52s: N/D")
    else:
        n_status, n_val, n_desc = "na", "N/D", "Histórico insuficiente."
        short_parts.append("Dist. Máx 52s: N/D")

    criteria_details.append({
        "letter": "N",
        "name": "New High (Proximidade do Topo 52s <= 15%)",
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
                else "Sem pico comprador no último pregão (meta: Volume >= 1.2x média 20d com alta)."
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
        "name": "Supply & Demand (Vol. Relativo >= 1.2x + Alta)",
        "status": s_status,
        "value": s_val,
        "description": s_desc
    })

    # --------------------------------------------------------------------------
    # L - Leader or Laggard (Força Relativa vs ^BVSP filtrando pela data inicial de hist_data)
    # --------------------------------------------------------------------------
    if hist_data is not None and len(hist_data) >= 2 and ibov_hist is not None and len(ibov_hist) >= 2:
        try:
            start_dt = pd.Timestamp(hist_data.index[0]).tz_localize(None)
            ibov_idx_naive = pd.to_datetime(ibov_hist.index).tz_localize(None)
            ibov_slice = ibov_hist[ibov_idx_naive >= start_dt]
            if len(ibov_slice) < 2:
                ibov_slice = ibov_hist.tail(len(hist_data))

            asset_start = float(hist_data['Close'].iloc[0])
            asset_end = float(hist_data['Close'].iloc[-1])
            ibov_start = float(ibov_slice['Close'].iloc[0])
            ibov_end = float(ibov_slice['Close'].iloc[-1])

            asset_ret_pct = ((asset_end / asset_start) - 1.0) * 100.0 if asset_start > 0 else 0.0
            ibov_ret_pct = ((ibov_end / ibov_start) - 1.0) * 100.0 if ibov_start > 0 else 0.0
            diff_ibov = asset_ret_pct - ibov_ret_pct

            l_status = "approved" if asset_ret_pct > ibov_ret_pct else "rejected"
            l_val = f"{diff_ibov:+.1f}% vs IBOV ({asset_ret_pct:+.1f}% vs {ibov_ret_pct:+.1f}%)"
            l_desc = (
                "Ativo líder: superou o Ibovespa na janela do gráfico selecionado."
                if l_status == "approved"
                else "Abaixo do índice: performance inferior ao Ibovespa no período selecionado."
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

    # Placar específico dos 5 critérios da ação (C, A, N, S, L)
    stock_score = sum(1 for item in criteria_details if item["status"] == "approved")
    stock_valid_criteria = sum(1 for item in criteria_details if item["status"] in ("approved", "rejected"))

    # --------------------------------------------------------------------------
    # M - Market Direction (Peso Principal via ^BVSP: MM50 e MM200 sobre 2y)
    # --------------------------------------------------------------------------
    market_regime = {
        "status": "ND",
        "ibov_close": None,
        "mm50": None,
        "mm200": None,
        "approved": False
    }

    if ibov_hist is not None and not ibov_hist.empty and len(ibov_hist) >= 50:
        try:
            ibov_close = float(ibov_hist['Close'].iloc[-1])
            mm50_ibov = float(ibov_hist['Close'].rolling(window=50).mean().iloc[-1])
            win_200 = min(200, len(ibov_hist))
            mm200_ibov = float(ibov_hist['Close'].rolling(window=win_200).mean().iloc[-1])

            if ibov_close > mm50_ibov and ibov_close > mm200_ibov:
                regime_status = "ALTA"
                m_status = "approved"
                regime_summary = "ALTA (acima MM50 e MM200)"
                m_val = f"ALTA ({ibov_close:,.0f} pts)"
                m_desc = (
                    f"Mercado: o mais importante. ^BVSP ({ibov_close:,.0f} pts) opera acima da MM50 ({mm50_ibov:,.0f}) "
                    f"e da MM200 ({mm200_ibov:,.0f}). Tendência primária e secundária de alta."
                )
            elif ibov_close < mm50_ibov and ibov_close < mm200_ibov:
                regime_status = "BAIXA"
                m_status = "rejected"
                regime_summary = "BAIXA (abaixo MM50 e MM200)"
                m_val = f"BAIXA ({ibov_close:,.0f} pts)"
                m_desc = (
                    f"Mercado: o mais importante. ^BVSP ({ibov_close:,.0f} pts) opera abaixo da MM50 ({mm50_ibov:,.0f}) "
                    f"e da MM200 ({mm200_ibov:,.0f}). Risco elevado — 3 de cada 4 ações caem junto com o índice."
                )
            else:
                regime_status = "ATENCAO"
                m_status = "rejected"
                regime_summary = "ATENCAO (entre MM50 e MM200)"
                m_val = f"ATENÇÃO ({ibov_close:,.0f} pts)"
                m_desc = (
                    f"Mercado em transição/cautela: ^BVSP ({ibov_close:,.0f} pts) entre a MM50 ({mm50_ibov:,.0f}) "
                    f"e a MM200 ({mm200_ibov:,.0f}). Exige seletividade redobrada."
                )

            market_regime = {
                "status": regime_status,
                "ibov_close": ibov_close,
                "mm50": mm50_ibov,
                "mm200": mm200_ibov,
                "approved": regime_status == "ALTA"
            }
        except Exception:
            m_status, m_val, m_desc = "na", "N/D", "Falha ao calcular MM50 e MM200 do ^BVSP."
            regime_summary = "N/D"
    else:
        m_status, m_val, m_desc = "na", "N/D", "Dados históricos de 2 anos do ^BVSP indisponíveis."
        regime_summary = "N/D"

    criteria_details.append({
        "letter": "M",
        "name": "Market Direction (Regime IBOV: MM50 & MM200)",
        "status": m_status,
        "value": m_val,
        "description": m_desc
    })

    score = sum(1 for item in criteria_details if item["status"] == "approved")
    valid_criteria = sum(1 for item in criteria_details if item["status"] in ("approved", "rejected"))

    summary_line = (
        f"Regime Mercado (IBOV): {regime_summary} | "
        f"Score Ativo (C-A-N-S-L): {stock_score}/{stock_valid_criteria} | "
        + " | ".join(short_parts)
    )

    return {
        "score": score,
        "valid_criteria": valid_criteria,
        "stock_score": stock_score,
        "stock_valid_criteria": stock_valid_criteria,
        "market_regime": market_regime,
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

