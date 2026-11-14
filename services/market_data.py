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


def _extract_ticker_fundamentals(ticker_obj) -> dict:
    """
    Extrai metadados fundamentalistas do ticker_obj (info, YoY trimestral para C
    e CAGR anual 3-4 anos para A) tratando falhas e ausências de forma segura.
    """
    try:
        info = ticker_obj.info or {}
    except Exception:
        info = {}

    # Fallback seguro para crescimento trimestral YoY (C)
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
                            info["_calc_quarterly_yoy_growth"] = (recent_val - yoy_prev_val) / abs(yoy_prev_val)
                            break
                        elif yoy_prev_val < 0 and recent_val <= 0:
                            info["_calc_quarterly_yoy_negative"] = True
                            break
    except Exception:
        pass

    # Cálculo do CAGR anual 3-4 anos (A)
    try:
        a_stmt = ticker_obj.income_stmt
        if a_stmt is not None and not a_stmt.empty:
            for row_label in ["Net Income", "Net Income Common Stockholders", "Diluted EPS", "Basic EPS"]:
                if row_label in a_stmt.index:
                    series = a_stmt.loc[row_label].dropna()
                    if len(series) >= 2:
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

    return info


@st.cache_data(ttl=CACHE_TTL_MARKET_DATA, show_spinner=False)
def fetch_stock_data(symbol: str, period: str):
    """
    Busca cotações e histórico OHLC via yfinance com cache configurado.
    Calcula médias móveis simples de 9 e 21 períodos.
    Aplica filtros rigorosos de sanitização para evitar glitches (ex: candles zerados à noite).
    Se o período do gráfico for curto ('1mo'), busca '3mo' para garantir os 63 pregões
    do critério L (Força Relativa 3M) e fatiar para exibição no gráfico.
    """
    ticker_obj = yf.Ticker(symbol)
    yf_period = PERIOD_MAPPING.get(period, "6mo")
    download_period = "3mo" if yf_period == "1mo" else yf_period

    hist = ticker_obj.history(period=download_period, interval="1d")

    if hist.empty:
        return None, {}

    # 1. Limpeza de linhas nulas ou zeradas (muito comum em consultas noturnas ou after-market)
    hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
    hist = hist[(hist['Open'] > 0) & (hist['High'] > 0) & (hist['Low'] > 0) & (hist['Close'] > 0)]

    # 2. Correção de anomalias pontuais onde o Low cai artificialmente para 0 ou valor absurdo
    if not hist.empty:
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

    info = _extract_ticker_fundamentals(ticker_obj)

    # Salva o retorno de 63 pregões (~3 meses) no info para que o critério L seja invariante ao período do gráfico
    if len(hist) >= 2:
        win_3m = min(63, len(hist))
        c_start_3m = float(hist['Close'].iloc[-win_3m])
        c_end_3m = float(hist['Close'].iloc[-1])
        if c_start_3m > 0:
            info["_asset_ret_63d_pct"] = ((c_end_3m / c_start_3m) - 1.0) * 100.0

    if yf_period == "1mo" and len(hist) > 22:
        hist = hist.tail(22)

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


def calculate_canslim_metrics(
    hist_data: pd.DataFrame,
    ticker_info: dict,
    ibov_hist: pd.DataFrame,
    strict_mode: bool = False
) -> dict:
    """
    Avalia os critérios quantitativos da metodologia CAN SLM com suporte a 2 perfis de rigor:
    - strict_mode=False ("Calibrado B3"): Limiares ajustados à realidade cíclica e de dividendos da B3.
    - strict_mode=True ("Estrito Livro O'Neil"): Limiares clássicos originais do livro.

    Critérios:
    C - Current Earnings: YoY > 20% (Estrito) ou > 12% (Calibrado B3)
    A - Annual Earnings:
        - Estrito: CAGR > 25% E ROE >= 17%
        - Calibrado B3: (CAGR > 15% e ROE >= 14%) OU (ROE >= 17% e CAGR > 5%)
    N - New High: Preço / Máxima 52s >= 0.85 (Estrito) ou >= 0.80 (Calibrado B3)
    S - Supply & Demand: Nos últimos 5 pregões, pelo menos 1 dia de alta (Close > Open ou Close > PrevClose)
        com Volume >= 1.25x a média móvel de volume de 20 dias.
    L - Leader or Laggard: Janela fixa de 63 pregões (~3 meses) superando o ^BVSP.
    M - Market Direction: ^BVSP avaliado contra MM50 e MM200 (ALTA, ATENCAO, BAIXA).
    """
    info = ticker_info if isinstance(ticker_info, dict) else {}
    criteria_details = []
    short_parts = []
    mode_tag = "Estrito O'Neil" if strict_mode else "Calibrado B3"

    # --------------------------------------------------------------------------
    # C - Current Earnings (Lucro Trimestral YoY)
    # --------------------------------------------------------------------------
    c_threshold = 0.20 if strict_mode else 0.12
    c_meta_str = "> 20%" if strict_mode else "> 12%"

    q_yoy = info.get("earningsQuarterlyGrowth")
    if q_yoy is None or pd.isna(q_yoy):
        q_yoy = info.get("_calc_quarterly_yoy_growth")

    if q_yoy is not None and not pd.isna(q_yoy):
        try:
            q_pct = float(q_yoy) * 100.0
            c_status = "approved" if float(q_yoy) > c_threshold else "rejected"
            c_val = f"YoY {q_pct:+.1f}%"
            c_desc = (
                f"Aprovado ({mode_tag}): Lucro/LPA trimestral cresceu {q_pct:+.1f}% YoY (Meta {c_meta_str})."
                if c_status == "approved"
                else f"Abaixo da meta ({mode_tag}): Lucro/LPA em {q_pct:+.1f}% YoY (Meta {c_meta_str})."
            )
            short_parts.append(f"LPA YoY: {q_pct:+.1f}%")
        except Exception:
            c_status, c_val, c_desc = "na", "N/D", f"Dados de LPA trimestral YoY indisponíveis (Meta {c_meta_str})."
            short_parts.append("LPA YoY: N/D")
    elif info.get("_calc_quarterly_yoy_negative"):
        c_status = "rejected"
        c_val = "Prejuízo Trim."
        c_desc = f"Resultado trimestral negativo no período atual e/ou anterior (Meta {c_meta_str})."
        short_parts.append("LPA YoY: Prejuízo")
    else:
        c_status, c_val, c_desc = "na", "N/D", f"Dados de lucro trimestral YoY indisponíveis (Meta {c_meta_str})."
        short_parts.append("LPA YoY: N/D")

    criteria_details.append({
        "letter": "C",
        "name": f"Current Earnings (Lucro Trim. YoY {c_meta_str})",
        "status": c_status,
        "value": c_val,
        "description": c_desc
    })

    # --------------------------------------------------------------------------
    # A - Annual Earnings (Lucro Anual & Rentabilidade)
    # --------------------------------------------------------------------------
    cagr_anual = info.get("_calc_annual_cagr")
    cagr_years = info.get("_calc_cagr_years", 3)
    cagr_nonpositive = info.get("_calc_annual_cagr_nonpositive", False)
    roe = info.get("returnOnEquity")

    has_cagr = cagr_anual is not None and not pd.isna(cagr_anual)
    has_roe = roe is not None and not pd.isna(roe)

    a_meta_title = (
        "Annual Earnings (CAGR > 25% + ROE >= 17%)"
        if strict_mode
        else "Annual Earnings (CAGR > 15% + ROE >= 14% ou ROE >= 17% + CAGR > 5%)"
    )
    a_meta_rule_str = (
        "Meta Estrita: CAGR > 25% e ROE >= 17%"
        if strict_mode
        else "Meta Calibrada B3: (CAGR > 15% e ROE >= 14%) ou (ROE >= 17% e CAGR > 5%)"
    )

    if has_cagr or has_roe or cagr_nonpositive:
        try:
            cagr_pct = float(cagr_anual) * 100.0 if has_cagr else None
            roe_pct = float(roe) * 100.0 if has_roe else None

            if cagr_nonpositive:
                a_status = "rejected"
                roe_str = f" | ROE {roe_pct:.1f}%" if roe_pct is not None else ""
                a_val = f"CAGR N/A (Prejuízo){roe_str}"
                a_desc = f"Balanço anual com prejuízo no período base ou recente ({a_meta_rule_str})."
                short_parts.append(f"CAGR Anual: Prejuízo ({f'ROE {roe_pct:.0f}%' if roe_pct is not None else 'ROE N/D'})")
            elif has_cagr and has_roe:
                c_val_f = float(cagr_anual)
                r_val_f = float(roe)
                if strict_mode:
                    is_approved = (c_val_f > 0.25) and (r_val_f >= 0.17)
                else:
                    is_approved = ((c_val_f > 0.15) and (r_val_f >= 0.14)) or ((r_val_f >= 0.17) and (c_val_f > 0.05))

                a_status = "approved" if is_approved else "rejected"
                a_val = f"CAGR {cagr_pct:+.1f}% ({cagr_years}a) | ROE {roe_pct:.1f}%"
                a_desc = (
                    f"Aprovado ({mode_tag}): CAGR anual de {cagr_pct:+.1f}% e ROE de {roe_pct:.1f}%. ({a_meta_rule_str})."
                    if is_approved
                    else f"Abaixo da meta ({mode_tag}): CAGR {cagr_pct:+.1f}% e ROE {roe_pct:.1f}%. ({a_meta_rule_str})."
                )
                short_parts.append(f"CAGR Anual: {cagr_pct:+.1f}% (ROE {roe_pct:.0f}%)")
            elif has_cagr and not has_roe:
                min_cagr_req = 0.25 if strict_mode else 0.05
                if float(cagr_anual) <= min_cagr_req:
                    a_status = "rejected"
                    a_val = f"CAGR {cagr_pct:+.1f}% ({cagr_years}a) | ROE N/D"
                    a_desc = f"CAGR anual de {cagr_pct:+.1f}% abaixo do piso exigido ({a_meta_rule_str})."
                else:
                    a_status = "na"
                    a_val = f"CAGR {cagr_pct:+.1f}% ({cagr_years}a) | ROE N/D"
                    a_desc = f"CAGR anual de {cagr_pct:+.1f}%, mas ROE indisponível no Yahoo Finance ({a_meta_rule_str})."
                short_parts.append(f"CAGR Anual: {cagr_pct:+.1f}% (ROE N/D)")
            else:
                min_roe_req = 0.17 if strict_mode else 0.14
                if float(roe) < min_roe_req:
                    a_status = "rejected"
                    a_val = f"CAGR N/D | ROE {roe_pct:.1f}%"
                    a_desc = f"ROE de {roe_pct:.1f}% abaixo do piso exigido ({a_meta_rule_str})."
                else:
                    a_status = "na"
                    a_val = f"CAGR N/D | ROE {roe_pct:.1f}%"
                    a_desc = f"ROE de {roe_pct:.1f}% atende ao piso, mas balanços anuais p/ CAGR indisponíveis ({a_meta_rule_str})."
                short_parts.append(f"CAGR Anual: N/D (ROE {roe_pct:.0f}%)")
        except Exception:
            a_status, a_val, a_desc = "na", "N/D", f"Falha ao calcular CAGR anual e ROE ({a_meta_rule_str})."
            short_parts.append("CAGR Anual: N/D")
    else:
        a_status, a_val, a_desc = "na", "N/D", f"Histórico anual de lucros e ROE indisponíveis ({a_meta_rule_str})."
        short_parts.append("CAGR Anual: N/D")

    criteria_details.append({
        "letter": "A",
        "name": a_meta_title,
        "status": a_status,
        "value": a_val,
        "description": a_desc
    })

    # --------------------------------------------------------------------------
    # N - New High (Proximidade da máxima de 52 semanas)
    # --------------------------------------------------------------------------
    n_threshold = 0.85 if strict_mode else 0.80
    n_max_dist_str = "15%" if strict_mode else "20%"

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
            n_status = "approved" if ratio_high >= n_threshold else "rejected"
            n_val = f"{dist_high_pct:+.1f}% (Topo: R$ {high_52w:.2f})"
            n_desc = (
                f"Aprovado ({mode_tag}): Negociando a {abs(dist_high_pct):.1f}% da máxima de 52s (Meta <= {n_max_dist_str} abaixo do topo)."
                if n_status == "approved"
                else f"Abaixo da meta ({mode_tag}): Distante {abs(dist_high_pct):.1f}% da máxima de 52s (Meta <= {n_max_dist_str} abaixo do topo)."
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
        "name": f"New High (Proximidade Topo 52s <= {n_max_dist_str})",
        "status": n_status,
        "value": n_val,
        "description": n_desc
    })

    # --------------------------------------------------------------------------
    # S - Supply & Demand (Janela de 5 pregões: >= 1 dia de alta com Vol >= 1.25x MM20)
    # --------------------------------------------------------------------------
    if hist_data is not None and len(hist_data) >= 6 and 'Volume' in hist_data.columns:
        vol_series = hist_data['Volume']
        vol_ma20_series = vol_series.rolling(window=20, min_periods=5).mean()
        fallback_ma20 = float(vol_series.tail(20).mean())

        if fallback_ma20 > 0:
            n_rows = len(hist_data)
            start_idx = max(1, n_rows - 5)
            has_accum_day = False
            max_rel_vol_5d = 0.0
            max_bull_rel_vol_5d = 0.0

            for idx in range(start_idx, n_rows):
                row = hist_data.iloc[idx]
                prev_row = hist_data.iloc[idx - 1]
                c_i = float(row['Close'])
                o_i = float(row['Open'])
                prev_c_i = float(prev_row['Close'])
                v_i = float(row['Volume'])

                ma20_i = float(vol_ma20_series.iloc[idx]) if pd.notna(vol_ma20_series.iloc[idx]) else fallback_ma20
                rel_v = (v_i / ma20_i) if ma20_i > 0 else 0.0

                if rel_v > max_rel_vol_5d:
                    max_rel_vol_5d = rel_v

                is_up = (c_i > o_i) or (c_i > prev_c_i)
                if is_up:
                    if rel_v > max_bull_rel_vol_5d:
                        max_bull_rel_vol_5d = rel_v
                    if rel_v >= 1.25:
                        has_accum_day = True

            peak_to_show = max_bull_rel_vol_5d if has_accum_day else max_rel_vol_5d
            s_status = "approved" if has_accum_day else "rejected"
            s_val = f"Pico Vol 5d: {peak_to_show:.2f}x"
            s_desc = (
                f"Acumulação institucional detectada: ao menos 1 pregão de alta nos últimos 5 dias com Volume >= 1.25x a média de 20d (Pico comprador: {max_bull_rel_vol_5d:.2f}x)."
                if s_status == "approved"
                else f"Sem dia de acumulação forte nos últimos 5 pregões (exige ao menos 1 pregão de alta com Volume >= 1.25x a MM20; maior pico 5d: {max_rel_vol_5d:.2f}x)."
            )
            short_parts.append(f"Pico Vol 5d: {peak_to_show:.2f}x")
        else:
            s_status, s_val, s_desc = "na", "N/D", "Volume de negociação indisponível."
            short_parts.append("Pico Vol 5d: N/D")
    else:
        s_status, s_val, s_desc = "na", "N/D", "Dados de volume insuficientes."
        short_parts.append("Pico Vol 5d: N/D")

    criteria_details.append({
        "letter": "S",
        "name": "Supply & Demand (Acumulação 5d: Vol >= 1.25x + Alta)",
        "status": s_status,
        "value": s_val,
        "description": s_desc
    })

    # --------------------------------------------------------------------------
    # L - Leader or Laggard (Força Relativa - Janela fixa de 63 pregões / ~3 meses)
    # --------------------------------------------------------------------------
    if hist_data is not None and len(hist_data) >= 2 and ibov_hist is not None and len(ibov_hist) >= 2:
        try:
            # Retorno de 63 pregões (~3 meses) do ativo (usa _asset_ret_63d_pct se o gráfico atual tiver < 63 barras)
            if len(hist_data) >= 63:
                asset_start_3m = float(hist_data['Close'].iloc[-63])
                asset_end_3m = float(hist_data['Close'].iloc[-1])
                var_ativo_3m = ((asset_end_3m / asset_start_3m) - 1.0) * 100.0 if asset_start_3m > 0 else 0.0
            elif info.get("_asset_ret_63d_pct") is not None:
                var_ativo_3m = float(info["_asset_ret_63d_pct"])
            else:
                asset_start_3m = float(hist_data['Close'].iloc[0])
                asset_end_3m = float(hist_data['Close'].iloc[-1])
                var_ativo_3m = ((asset_end_3m / asset_start_3m) - 1.0) * 100.0 if asset_start_3m > 0 else 0.0

            # Retorno de 63 pregões (~3 meses) do ^BVSP
            win_ibov_3m = min(63, len(ibov_hist))
            ibov_start_3m = float(ibov_hist['Close'].iloc[-win_ibov_3m])
            ibov_end_3m = float(ibov_hist['Close'].iloc[-1])
            var_ibov_3m = ((ibov_end_3m / ibov_start_3m) - 1.0) * 100.0 if ibov_start_3m > 0 else 0.0

            diff_ibov_3m = var_ativo_3m - var_ibov_3m

            l_status = "approved" if var_ativo_3m > var_ibov_3m else "rejected"
            l_val = f"{diff_ibov_3m:+.1f}% vs IBOV 3M ({var_ativo_3m:+.1f}% vs {var_ibov_3m:+.1f}%)"
            l_desc = (
                f"Ativo líder: superou o Ibovespa na janela fixa de 63 pregões / 3 meses ({var_ativo_3m:+.1f}% vs {var_ibov_3m:+.1f}%)."
                if l_status == "approved"
                else f"Abaixo do índice: performance inferior ao Ibovespa nos últimos 63 pregões / 3 meses ({var_ativo_3m:+.1f}% vs {var_ibov_3m:+.1f}%)."
            )
            short_parts.append(f"vs IBOV 3M: {diff_ibov_3m:+.1f}%")
        except Exception:
            l_status, l_val, l_desc = "na", "N/D", "Não foi possível comparar os últimos 63 pregões com o Ibovespa."
            short_parts.append("vs IBOV 3M: N/D")
    else:
        l_status, l_val, l_desc = "na", "N/D", "Dados do Ibovespa indisponíveis para comparação de 3 meses."
        short_parts.append("vs IBOV 3M: N/D")

    criteria_details.append({
        "letter": "L",
        "name": "Leader or Laggard (Força Relativa 3M / 63d vs IBOV)",
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
        f"Score Ativo ({mode_tag} C-A-N-S-L): {stock_score}/{stock_valid_criteria} | "
        + " | ".join(short_parts)
    )

    return {
        "score": score,
        "valid_criteria": valid_criteria,
        "stock_score": stock_score,
        "stock_valid_criteria": stock_valid_criteria,
        "strict_mode": strict_mode,
        "mode_label": mode_tag,
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
def _fetch_raw_b3_scanner_data(asset_tuple: tuple) -> list[dict]:
    """
    Coleta em paralelo (ThreadPoolExecutor) o histórico de 6 meses e os metadados
    fundamentalistas de cada ticker da lista, mantendo em cache por 15 minutos (900s).
    Separar o download bruto do cálculo permite alternar entre 'Calibrado B3' e
    'Estrito Livro (O'Neil)' no Radar B3 instantaneamente (<10ms) sem novo download.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _download_single(ticker: str):
        try:
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(period="6mo", interval="1d")

            if hist is None or hist.empty or len(hist) < 22:
                return None

            hist = hist.dropna(subset=['Open', 'High', 'Low', 'Close'])
            hist = hist[(hist['Open'] > 0) & (hist['High'] > 0) & (hist['Low'] > 0) & (hist['Close'] > 0)]

            if len(hist) < 22:
                return None

            hist['SMA9'] = hist['Close'].rolling(window=9).mean()
            hist['SMA21'] = hist['Close'].rolling(window=21).mean()

            info = _extract_ticker_fundamentals(ticker_obj)
            return {
                "ticker": ticker,
                "hist": hist,
                "info": info
            }
        except Exception:
            return None

    raw_items = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(_download_single, t): t for t in asset_tuple}
        for future in as_completed(future_map):
            res = future.result()
            if res is not None:
                raw_items.append(res)
    return raw_items


def scan_b3_market_opportunities(
    asset_list: list = None,
    scan_all: bool = True,
    strict_mode: bool = False
) -> list[dict]:
    """
    Escaneia os ativos populares da B3 combinando tendência técnica (MMA 9 e 21) com
    o Score Quantitativo do Ativo CAN SLM (C-A-N-S-L) conforme o Perfil de Rigor
    selecionado ('Calibrado B3' ou 'Estrito Livro O'Neil').
    """
    from config import PopularB3Asset

    if asset_list is None:
        raw_list = [
            asset.value.split(" - ")[0].strip()
            for asset in PopularB3Asset
            if asset != PopularB3Asset.OUTRO
        ]
        asset_list = raw_list if scan_all else raw_list[:20]

    ibov_hist = fetch_ibov_data()
    raw_items = _fetch_raw_b3_scanner_data(tuple(asset_list))
    mode_tag = "Estrito O'Neil" if strict_mode else "Calibrado B3"

    results = []
    for item in raw_items:
        try:
            ticker = item["ticker"]
            hist = item["hist"]
            info = item["info"]

            last = hist.iloc[-1]
            prev = hist.iloc[-2]

            price = float(last['Close'])
            sma9 = float(last['SMA9'])
            sma21 = float(last['SMA21'])
            prev_price = float(prev['Close'])
            daily_pct = ((price - prev_price) / prev_price) * 100.0 if prev_price else 0.0

            if len(hist) >= 6:
                c5 = float(hist['Close'].iloc[-6])
                var5d = ((price - c5) / c5) * 100.0 if c5 else 0.0
            else:
                var5d = daily_pct

            c21 = float(hist['Close'].iloc[-21])
            var21d = ((price - c21) / c21) * 100.0 if c21 else 0.0

            canslim = calculate_canslim_metrics(hist, info, ibov_hist, strict_mode=strict_mode)
            cs_score = canslim.get("stock_score", 0)
            cs_valid = canslim.get("stock_valid_criteria", 5)
            cs_ratio = (cs_score / cs_valid) if cs_valid > 0 else 0.0
            cs_details = [
                d for d in canslim.get("criteria_details", [])
                if d.get("letter") in ("C", "A", "N", "S", "L")
            ]

            company = B3_ASSET_NAMES.get(ticker.replace(".SA", ""), ticker.replace(".SA", ""))
            canslim_bonus = (cs_score * 5.0) + (cs_ratio * 10.0)

            # 1. Compra Forte: Alinhamento técnico de alta + forte Score Quantitativo CAN SLM (>= 3 ou >= 60%)
            if price > sma9 > sma21 and var5d > 0 and (cs_score >= 3 or cs_ratio >= 0.60):
                sinal = "🟢 Compra Forte (Líder CAN SLM)"
                categoria = "COMPRA"
                score = 100 + canslim_bonus + min(var5d, 10)
                motivo = (
                    f"Alinhamento técnico (Preço > MMA9 > MMA21) com forte Score "
                    f"CAN SLM [{mode_tag}] ({cs_score}/{cs_valid} aprovados)."
                )

            # 2. Tendência de Alta: Tendência técnica compradora sustentada acima da MMA21
            elif price > sma21 and sma9 > sma21:
                sinal = "🟢 Tendência de Alta"
                categoria = "COMPRA"
                score = 80 + canslim_bonus + min(var5d, 10)
                motivo = (
                    f"Tendência compradora acima da MMA 21 | Score CAN SLM [{mode_tag}]: {cs_score}/{cs_valid}."
                )

            # 3. Ficar de Olho: Rompimento técnico OU alto Score Quantitativo CAN SLM (>= 3) em pullback/consolidação
            elif (
                (price > sma21 and prev['Close'] <= sma21)
                or (sma9 > sma21 and prev['SMA9'] <= prev['SMA21'])
                or (price > sma9 and var5d > 1.5)
                or (cs_score >= 3 and price >= sma21 * 0.96)
            ):
                sinal = "🟡 Ficar de Olho"
                categoria = "OLHO"
                score = 65 + canslim_bonus + min(var5d, 10)
                if cs_score >= 3 and not (price > sma21 and sma9 > sma21):
                    motivo = (
                        f"Forte fundamento CAN SLM [{mode_tag}] ({cs_score}/{cs_valid}) em região de pullback/consolidação."
                    )
                else:
                    motivo = (
                        f"Reversão ou rompimento altista das médias | Score CAN SLM [{mode_tag}]: {cs_score}/{cs_valid}."
                    )

            # 4. Em consolidação / neutro
            elif abs(price - sma21) / sma21 < 0.015:
                sinal = "⚪ Neutro / Lateral"
                categoria = "NEUTRO"
                score = 45 + canslim_bonus
                motivo = f"Ativo testando região de médias | Score CAN SLM [{mode_tag}]: {cs_score}/{cs_valid}."

            # 5. Baixa
            else:
                sinal = "🔴 Baixa / Correção"
                categoria = "BAIXA"
                score = 20 + canslim_bonus + max(var5d, -20)
                motivo = f"Preço abaixo das médias móveis de curto/médio prazo | Score CAN SLM [{mode_tag}]: {cs_score}/{cs_valid}."

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
                "motivo": motivo,
                "canslim_score": cs_score,
                "canslim_valid": cs_valid,
                "canslim_ratio": cs_ratio,
                "canslim_details": cs_details,
                "strict_mode": strict_mode,
                "mode_label": mode_tag,
                "market_regime": canslim.get("market_regime", {})
            })
        except Exception:
            continue

    results.sort(key=lambda x: (x["score"], x.get("canslim_score", 0)), reverse=True)
    return results

