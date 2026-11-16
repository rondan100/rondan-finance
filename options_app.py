"""
Simulador Visual de Opções de Ações da B3 (Call e Put) — Aplicativo Independente.
Para executar:
    streamlit run options_app.py
"""

import math
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import PopularB3Asset, B3_ASSET_NAMES
from services.market_data import normalize_ticker, fetch_stock_data


# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILOS (MOBILE-FRIENDLY)
# ==============================================================================
st.set_page_config(
    page_title="Simulador Visual de Opções B3 (Call & Put)",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .opt-banner-win {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.88) 0%, rgba(16, 185, 129, 0.25) 100%);
        border: 1px solid #10b981;
        border-left: 6px solid #10b981;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 10px 0 14px 0;
        color: #ecfdf5;
    }
    .opt-banner-loss {
        background: linear-gradient(135deg, rgba(127, 29, 29, 0.88) 0%, rgba(239, 68, 68, 0.25) 100%);
        border: 1px solid #ef4444;
        border-left: 6px solid #ef4444;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 10px 0 14px 0;
        color: #fef2f2;
    }
    .opt-banner-even {
        background: linear-gradient(135deg, rgba(120, 53, 15, 0.85) 0%, rgba(245, 158, 11, 0.25) 100%);
        border: 1px solid #f59e0b;
        border-left: 6px solid #f59e0b;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 10px 0 14px 0;
        color: #fffbeb;
    }
    @media (max-width: 768px) {
        .opt-banner-win, .opt-banner-loss, .opt-banner-even {
            padding: 12px 14px;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# FUNÇÕES MATEMÁTICAS — BLACK-SCHOLES (SEM SCIPY) E VOLATILIDADE
# ==============================================================================
def _norm_cdf(x: float) -> float:
    """Função de distribuição acumulada normal padrão usando math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    is_call: bool = True
) -> float:
    """
    Calcula o prêmio teórico justo de uma opção europeia via Black-Scholes.
    S: Preço atual da ação
    K: Strike (preço de exercício)
    T: Tempo até o vencimento em anos (dias_uteis / 252)
    r: Taxa livre de risco anualizada (ex: 0.1125 = 11,25% a.a.)
    sigma: Volatilidade histórica anualizada (ex: 0.30 = 30% a.a.)
    is_call: True para CALL, False para PUT
    """
    if S <= 0 or K <= 0:
        return 0.01
    if T <= 0 or sigma <= 0:
        intrinsic = max(0.0, S - K) if is_call else max(0.0, K - S)
        return max(0.01, intrinsic)

    try:
        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * (sigma ** 2)) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        if is_call:
            price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        else:
            price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

        return max(0.01, float(price))
    except Exception:
        intrinsic = max(0.0, S - K) if is_call else max(0.0, K - S)
        return max(0.01, intrinsic)


def calculate_historical_volatility(hist: pd.DataFrame) -> float:
    """
    Calcula a volatilidade histórica anualizada a partir dos retornos diários:
    std() * (252 ** 0.5). Retorna fallback de 0.30 (30%) caso insuficiente.
    """
    if hist is None or hist.empty or len(hist) < 5:
        return 0.30
    returns = hist["Close"].pct_change().dropna()
    if len(returns) < 3:
        return 0.30
    vol = float(returns.std() * (252 ** 0.5))
    if pd.isna(vol) or vol <= 0.01:
        return 0.30
    return min(max(vol, 0.10), 1.50)


def project_expiry_date(last_dt: pd.Timestamp, business_days: int) -> pd.Timestamp:
    """
    Projeta a data de vencimento adicionando N dias úteis (business days) à data atual.
    """
    base_dt = pd.Timestamp(last_dt).tz_localize(None)
    future_bdays = pd.bdate_range(start=base_dt, periods=business_days + 1)
    return future_bdays[-1]


# ==============================================================================
# 1. BARRA LATERAL — SELEÇÃO DO ATIVO E PARÂMETROS DA OPERAÇÃO
# ==============================================================================
with st.sidebar:
    st.title("🎯 Simulador de Opções B3")
    st.caption("Versão `v1.6.1` — Simule operações de **Call** e **Put** (Compra ou Venda) com visualização de zonas de lucro e prejuízo.")
    st.markdown("---")

    st.subheader("1️⃣ Ativo e Histórico")
    asset_options = [asset.value for asset in PopularB3Asset]
    selected_asset_option = st.selectbox(
        "Selecione a Ação da B3:",
        options=asset_options,
        index=0,
        help="Escolha uma ação líquida da B3 ou selecione OUTRO para digitar manualmente."
    )

    if selected_asset_option == PopularB3Asset.OUTRO.value:
        custom_ticker = st.text_input("Digite o código do Ativo (ex: BHIA3,PRIO3):", value="PETR4")
        raw_ticker = custom_ticker
    else:
        raw_ticker = selected_asset_option.split(" - ")[0].strip()

    ticker_normalized = normalize_ticker(raw_ticker)
    clean_code = ticker_normalized.replace(".SA", "")
    company_name = B3_ASSET_NAMES.get(clean_code, clean_code)

    hist_period_choice = st.radio(
        "Período Histórico do Gráfico:",
        options=["1mo", "3mo"],
        index=0,
        horizontal=True,
        help="Janela histórica recente exibida à esquerda da linha 'Hoje' no gráfico Candlestick."
    )

# Busca de dados via módulo existente (reaproveitando cache e sanitização de market_data.py)
period_key_map = {"1mo": "1m", "3mo": "3m"}
with st.spinner(f"Buscando cotações e volatilidade de {ticker_normalized}..."):
    hist_data, _ = fetch_stock_data(ticker_normalized, period_key_map.get(hist_period_choice, "1m"))

if hist_data is None or hist_data.empty:
    st.error(f"❌ Não foi possível carregar os dados históricos para **{ticker_normalized}**. Verifique o código do ativo.")
    st.stop()

current_price = float(hist_data["Close"].iloc[-1])
prev_close = float(hist_data["Close"].iloc[-2]) if len(hist_data) > 1 else current_price
daily_change_pct = ((current_price - prev_close) / prev_close) * 100.0 if prev_close else 0.0
hist_vol = calculate_historical_volatility(hist_data)
RISK_FREE_RATE = 0.1125  # Taxa livre de risco referência (11,25% a.a.)

# Sincronização automática de estado quando o usuário troca de ativo
if st.session_state.get("opt_last_ticker") != ticker_normalized:
    st.session_state["opt_last_ticker"] = ticker_normalized
    st.session_state["opt_strike_val"] = round(current_price, 2)
    st.session_state["opt_sim_price"] = round(current_price, 2)
    st.session_state.pop("opt_last_bs_sig", None)

with st.sidebar:
    st.markdown("---")
    st.subheader("2️⃣ Estrutura da Opção")

    option_type_label = st.radio(
        "Tipo de Opção:",
        options=["CALL (Opção de Compra)", "PUT (Opção de Venda)"],
        horizontal=False,
        help="CALL ganha com a valorização (ou protege contra alta); PUT ganha com a queda (ou protege a carteira)."
    )
    is_call = option_type_label.startswith("CALL")

    side_label = st.radio(
        "Ponta da Operação:",
        options=["COMPRA (Titular)", "VENDA (Lançador)"],
        horizontal=False,
        help="COMPRA (Titular): paga o prêmio e tem o direito de exercer.\nVENDA (Lançador): recebe o prêmio inicialmente e assume a obrigação."
    )
    is_long = side_label.startswith("COMPRA")

    days_to_expiry = st.number_input(
        "Dias Úteis até o Vencimento:",
        min_value=1,
        max_value=90,
        value=21,
        step=1,
        help="Quantidade de pregões (dias úteis) até o vencimento da série da opção (21 dias úteis ≈ 1 mês)."
    )

    strike_price = st.number_input(
        "Strike / Preço de Exercício (R$):",
        min_value=0.10,
        max_value=max(1000.0, current_price * 5.0),
        value=float(st.session_state.get("opt_strike_val", round(current_price, 2))),
        step=0.25,
        format="%.2f",
        key="opt_strike_val",
        help="Preço contratado para comprar (Call) ou vender (Put) a ação no vencimento."
    )

    # Cálculo do prêmio teórico justo via Black-Scholes
    T_years = float(days_to_expiry) / 252.0
    bs_fair_premium = round(
        black_scholes_price(
            S=current_price,
            K=float(strike_price),
            T=T_years,
            r=RISK_FREE_RATE,
            sigma=hist_vol,
            is_call=is_call
        ),
        2
    )

    # Atualiza o prêmio sugerido quando mudam os parâmetros estruturais (ativo, tipo, strike ou dias)
    bs_signature = (ticker_normalized, is_call, round(float(strike_price), 2), int(days_to_expiry))
    if st.session_state.get("opt_last_bs_sig") != bs_signature:
        st.session_state["opt_last_bs_sig"] = bs_signature
        st.session_state["opt_premium_val"] = bs_fair_premium

    premium = st.number_input(
        "Prêmio por Opção (R$):",
        min_value=0.01,
        max_value=max(500.0, current_price * 2.0),
        value=float(st.session_state.get("opt_premium_val", bs_fair_premium)),
        step=0.05,
        format="%.2f",
        key="opt_premium_val",
        help="Valor pago (na Compra) ou recebido (na Venda) por cada opção. Pré-preenchido via Black-Scholes, mas editável."
    )
    st.caption(
        f"💡 **Justo Black-Scholes:** `R$ {bs_fair_premium:.2f}` "
        f"*(Vol. Histórica: {hist_vol * 100:.1f}% a.a. | Taxa: {RISK_FREE_RATE * 100:.2f}% a.a.)*"
    )

    qty_options = st.number_input(
        "Quantidade de Opções:",
        min_value=100,
        max_value=1_000_000,
        value=100,
        step=100,
        help="Lote padrão de opções na B3 (múltiplos de 100 unidades)."
    )

    st.markdown("---")
    if st.button("🔄 Recalibrar Prêmio p/ Black-Scholes", use_container_width=True):
        st.session_state["opt_premium_val"] = bs_fair_premium
        st.rerun()


# ==============================================================================
# CABEÇALHO PRINCIPAL E RESUMO DO ATIVO
# ==============================================================================
last_candle_dt = pd.Timestamp(hist_data.index[-1]).tz_localize(None)
expiry_dt = project_expiry_date(last_candle_dt, int(days_to_expiry))

op_title_str = f"{'Compra (Titular)' if is_long else 'Venda (Lançador)'} de {'CALL' if is_call else 'PUT'}"
st.title(f"🎯 Simulador Visual de Opções B3 — {clean_code} ({company_name})")
st.markdown(
    f"Operação selecionada: **{op_title_str}** &nbsp;|&nbsp; "
    f"Strike: **`R$ {strike_price:.2f}`** &nbsp;|&nbsp; "
    f"Prêmio: **`R$ {premium:.2f}`** &nbsp;|&nbsp; "
    f"Vencimento projetado: **`{expiry_dt.strftime('%d/%m/%Y')}`** (*{days_to_expiry} dias úteis*)"
)

# Métricas do ativo subjacente
top_c1, top_c2, top_c3, top_c4 = st.columns(4)
with top_c1:
    st.metric(
        f"Cotação Atual ({clean_code})",
        f"R$ {current_price:.2f}",
        f"{daily_change_pct:+.2f}% no dia",
        help="Último preço de fechamento/negociação da ação na B3."
    )
with top_c2:
    moneyness_diff = ((current_price - strike_price) / strike_price) * 100.0
    if is_call:
        m_status = "ITM (Dentro do Dinheiro)" if current_price > strike_price * 1.005 else (
            "OTM (Fora do Dinheiro)" if current_price < strike_price * 0.995 else "ATM (No Dinheiro)"
        )
    else:
        m_status = "ITM (Dentro do Dinheiro)" if current_price < strike_price * 0.995 else (
            "OTM (Fora do Dinheiro)" if current_price > strike_price * 1.005 else "ATM (No Dinheiro)"
        )
    st.metric(
        "Strike da Opção",
        f"R$ {strike_price:.2f}",
        m_status,
        delta_color="off",
        help="Preço de exercício contratado e classificação atual (ITM / ATM / OTM)."
    )
with top_c3:
    st.metric(
        "Prêmio Unitário (BS / Editado)",
        f"R$ {premium:.2f}",
        f"Teórico BS: R$ {bs_fair_premium:.2f}",
        delta_color="off",
        help="Prêmio considerado na simulação comparado ao preço justo calculado por Black-Scholes."
    )
with top_c4:
    st.metric(
        "Volatilidade Histórica (Anual)",
        f"{hist_vol * 100:.1f}%",
        f"{days_to_expiry} d.u. até {expiry_dt.strftime('%d/%m')}",
        delta_color="off",
        help="Volatilidade histórica anualizada calculada sobre os retornos diários recentes (std * √252)."
    )

st.markdown("---")


# ==============================================================================
# 3. SIMULADOR INTERATIVO DE PREÇO NO VENCIMENTO (SLIDER EM DESTAQUE)
# ==============================================================================
min_sim_price = max(0.05, round((current_price * 0.70) / 0.05) * 0.05)
max_sim_price = round((current_price * 1.30) / 0.05) * 0.05
default_sim_price = round(current_price / 0.05) * 0.05
default_sim_price = min(max(default_sim_price, min_sim_price), max_sim_price)

if "opt_sim_price" not in st.session_state:
    st.session_state["opt_sim_price"] = default_sim_price
else:
    st.session_state["opt_sim_price"] = min(max(float(st.session_state["opt_sim_price"]), min_sim_price), max_sim_price)

st.subheader("🎚️ Simulador de Cenário no Vencimento")
simulated_price = st.slider(
    "🎯 Simular Preço da Ação no Vencimento (R$) — arraste entre -30% e +30% do preço atual:",
    min_value=float(min_sim_price),
    max_value=float(max_sim_price),
    value=float(st.session_state["opt_sim_price"]),
    step=0.05,
    format="R$ %.2f",
    key="opt_sim_price",
    help="Arraste a barra para simular qualquer cotação da ação na data de vencimento e ver o resultado financeiro em tempo real."
)

sim_var_from_spot_pct = ((simulated_price - current_price) / current_price) * 100.0 if current_price else 0.0

# Cálculos Financeiros da Operação
breakeven = (strike_price + premium) if is_call else max(0.0, strike_price - premium)
breakeven_dist_pct = ((breakeven - current_price) / current_price) * 100.0 if current_price else 0.0
total_cash_flow = float(premium) * int(qty_options)  # Custo pago (Compra) ou Crédito recebido (Venda)

if is_call and is_long:
    # Compra de Call (Titular)
    pnl_reais = (max(0.0, simulated_price - strike_price) - premium) * qty_options
    max_profit_str = "Ilimitado (acompanha alta da ação)"
    max_loss_str = f"R$ {total_cash_flow:,.2f} (100% do prêmio pago)"
    cash_label = "Custo Total (Débito Pago)"
    profit_above_be = True
elif is_call and not is_long:
    # Venda de Call (Lançador)
    pnl_reais = (premium - max(0.0, simulated_price - strike_price)) * qty_options
    max_profit_str = f"R$ {total_cash_flow:,.2f} (limitado ao prêmio recebido)"
    max_loss_str = "Ilimitado a descoberto (se a ação disparar)"
    cash_label = "Crédito Total Recebido"
    profit_above_be = False
elif (not is_call) and is_long:
    # Compra de Put (Titular)
    pnl_reais = (max(0.0, strike_price - simulated_price) - premium) * qty_options
    max_profit_val = max(0.0, (strike_price - premium) * qty_options)
    max_profit_str = f"R$ {max_profit_val:,.2f} (se a ação cair a R$ 0)"
    max_loss_str = f"R$ {total_cash_flow:,.2f} (100% do prêmio pago)"
    cash_label = "Custo Total (Débito Pago)"
    profit_above_be = False
else:
    # Venda de Put (Lançador)
    pnl_reais = (premium - max(0.0, strike_price - simulated_price)) * qty_options
    max_profit_str = f"R$ {total_cash_flow:,.2f} (limitado ao prêmio recebido)"
    max_loss_val = max(0.0, (strike_price - premium) * qty_options)
    max_loss_str = f"R$ {max_loss_val:,.2f} (se a ação cair a R$ 0)"
    cash_label = "Crédito Total Recebido"
    profit_above_be = True

pnl_pct = (pnl_reais / total_cash_flow) * 100.0 if total_cash_flow > 0 else 0.0


# ==============================================================================
# 5. CARDS DE RESULTADO EM DESTAQUE
# ==============================================================================
if pnl_reais > 0.005:
    banner_cls = "opt-banner-win"
    verdict_icon = "🟢"
    verdict_title = f"GANHOU R$ {pnl_reais:,.2f} ({pnl_pct:+.1f}% sobre o prêmio)"
    marker_color = "#00c853"
elif pnl_reais < -0.005:
    banner_cls = "opt-banner-loss"
    verdict_icon = "🔴"
    verdict_title = f"PERDEU -R$ {abs(pnl_reais):,.2f} ({pnl_pct:+.1f}% sobre o prêmio)"
    marker_color = "#ff1744"
else:
    banner_cls = "opt-banner-even"
    verdict_icon = "🟡"
    verdict_title = "NO ZERO A ZERO (Ponto de Empate / Breakeven Exato)"
    marker_color = "#f59e0b"

st.markdown(f"""
<div class="{banner_cls}">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
            <span style="font-size:1.35rem;font-weight:800;">{verdict_icon} {verdict_title}</span>
            <div style="font-size:0.95rem;opacity:0.92;margin-top:4px;">
                Cenário simulado no vencimento (<b>{expiry_dt.strftime('%d/%m/%Y')}</b>):
                Ação a <b>R$ {simulated_price:.2f}</b> ({sim_var_from_spot_pct:+.1f}% vs cotação de hoje R$ {current_price:.2f})
            </div>
        </div>
        <div style="text-align:right;font-size:0.92rem;background:rgba(0,0,0,0.25);padding:8px 14px;border-radius:8px;">
            <b>{op_title_str}</b><br>
            Lote: <b>{int(qty_options)} opções</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

res_c1, res_c2, res_c3, res_c4 = st.columns(4)
with res_c1:
    be_dir_str = "subir" if breakeven > current_price else ("cair" if breakeven < current_price else "manter")
    st.metric(
        "Ponto de Empate (Breakeven)",
        f"R$ {breakeven:.2f}",
        f"Ativo precisa {be_dir_str} {abs(breakeven_dist_pct):.2f}%",
        delta_color="off",
        help="Preço exato que a ação precisa atingir no vencimento para empatar o prêmio pago/recebido."
    )
with res_c2:
    st.metric(
        cash_label,
        f"R$ {total_cash_flow:,.2f}",
        f"{int(qty_options)}x R$ {premium:.2f}",
        delta_color="off",
        help="Valor total desembolsado (na compra) ou embolsado inicialmente (na venda)."
    )
with res_c3:
    st.metric(
        "Lucro Máximo Possível",
        max_profit_str.split(" (")[0],
        max_profit_str.split(" (")[1].rstrip(")") if "(" in max_profit_str else "",
        delta_color="normal",
        help="Ganho máximo teórico da estrutura no vencimento."
    )
with res_c4:
    st.metric(
        "Risco / Prejuízo Máximo",
        max_loss_str.split(" (")[0],
        max_loss_str.split(" (")[1].rstrip(")") if "(" in max_loss_str else "",
        delta_color="inverse",
        help="Perda máxima possível caso o cenário vá totalmente contra a posição."
    )


# ==============================================================================
# 4. GRÁFICO CANDLESTICK COM ZONAS VERDE (LUCRO) E VERMELHA (PREJUÍZO)
# ==============================================================================
st.subheader("📊 Gráfico Candlestick + Janela de Projeção até o Vencimento")
st.caption(
    "À esquerda da linha **Hoje**, veja o histórico real da ação. À direita (até o **Vencimento**), "
    "a **Faixa Verde** destaca a região onde a operação dá **LUCRO** e a **Faixa Vermelha** onde dá **PREJUÍZO**."
)

plot_df = hist_data.copy()
plot_df.index = pd.to_datetime(plot_df.index).tz_localize(None)

# Determinar limites verticais confortáveis para o gráfico e para as faixas de lucro/prejuízo
hist_min = float(plot_df["Low"].min())
hist_max = float(plot_df["High"].max())
y_floor = max(0.05, min(hist_min, min_sim_price, breakeven, strike_price) * 0.92)
y_ceil = max(hist_max, max_sim_price, breakeven, strike_price) * 1.08

fig = go.Figure()

# 1. Candles históricos até Hoje
fig.add_trace(
    go.Candlestick(
        x=plot_df.index,
        open=plot_df["Open"],
        high=plot_df["High"],
        low=plot_df["Low"],
        close=plot_df["Close"],
        name=f"{clean_code} (Histórico)",
        increasing_line_color="#00e676",
        decreasing_line_color="#ff5252"
    )
)

# 2. Linha de trajetória projetada entre Hoje e o Preço Simulado no Vencimento
fig.add_trace(
    go.Scatter(
        x=[last_candle_dt, expiry_dt],
        y=[current_price, simulated_price],
        mode="lines+markers+text",
        name="Preço Simulado no Vencimento",
        line=dict(color=marker_color, width=3, dash="dot"),
        marker=dict(
            size=[8, 16],
            color=["#60a5fa", marker_color],
            line=dict(width=2, color="#ffffff"),
            symbol=["circle", "diamond"]
        ),
        text=["", f"  Simulado: R$ {simulated_price:.2f} ({pnl_reais:+,.0f} R$)"],
        textposition="middle right",
        textfont=dict(color=marker_color, size=13, family="Arial Black"),
        hovertemplate="Data: %{x|%d/%m/%Y}<br>Preço: R$ %{y:.2f}<extra></extra>"
    )
)

# Calcula a fração horizontal (0 a 1 do eixo X) onde começa a janela futura ("Hoje" -> "Vencimento")
x_start_dt = plot_df.index[0]
x_end_pad = expiry_dt + timedelta(days=max(4, int(days_to_expiry * 0.25)))
total_span_sec = max(1.0, (x_end_pad - x_start_dt).total_seconds())
today_offset_sec = max(0.0, (last_candle_dt - x_start_dt).total_seconds())
x0_future_frac = min(max(today_offset_sec / total_span_sec, 0.15), 0.88)

# 3. Faixas Verde (Lucro) e Vermelha (Prejuízo) na janela futura divididas pelo Breakeven
if profit_above_be:
    green_y0, green_y1 = breakeven, y_ceil
    red_y0, red_y1 = y_floor, breakeven
    green_pos, red_pos = "top right", "bottom right"
else:
    green_y0, green_y1 = y_floor, breakeven
    red_y0, red_y1 = breakeven, y_ceil
    green_pos, red_pos = "bottom right", "top right"

fig.add_hrect(
    y0=green_y0,
    y1=green_y1,
    x0=x0_future_frac,
    x1=1.0,
    fillcolor="rgba(0, 200, 83, 0.22)",
    line_width=0,
    annotation_text="🟢 ZONA DE LUCRO NO VENCIMENTO",
    annotation_position=green_pos,
    annotation_font=dict(color="#00e676", size=12)
)

fig.add_hrect(
    y0=red_y0,
    y1=red_y1,
    x0=x0_future_frac,
    x1=1.0,
    fillcolor="rgba(255, 23, 68, 0.22)",
    line_width=0,
    annotation_text="🔴 ZONA DE PREJUÍZO NO VENCIMENTO",
    annotation_position=red_pos,
    annotation_font=dict(color="#ff5252", size=12)
)

# 4. Linhas Horizontais Pontilhadas de Referência: Strike e Breakeven
fig.add_hline(
    y=strike_price,
    line_dash="dot",
    line_color="#60a5fa",
    line_width=1.8,
    annotation_text=f"Strike: R$ {strike_price:.2f}",
    annotation_position="top left",
    annotation_font=dict(color="#93c5fd", size=11)
)

fig.add_hline(
    y=breakeven,
    line_dash="dot",
    line_color="#fbbf24",
    line_width=2.2,
    annotation_text=f"Breakeven (Empate): R$ {breakeven:.2f}",
    annotation_position="bottom left",
    annotation_font=dict(color="#fde68a", size=12)
)

# 5. Linhas Verticais Tracejadas: "Hoje" e "Vencimento"
fig.add_vline(
    x=last_candle_dt,
    line_dash="dash",
    line_color="#9ca3af",
    line_width=1.8
)
fig.add_annotation(
    x=last_candle_dt,
    y=y_ceil,
    text=f"Hoje ({last_candle_dt.strftime('%d/%m')})",
    showarrow=False,
    yshift=-12,
    font=dict(color="#e5e7eb", size=11),
    bgcolor="rgba(17, 24, 39, 0.8)"
)

fig.add_vline(
    x=expiry_dt,
    line_dash="dash",
    line_color="#f59e0b",
    line_width=2.0
)
fig.add_annotation(
    x=expiry_dt,
    y=y_ceil,
    text=f"Vencimento ({expiry_dt.strftime('%d/%m/%Y')})",
    showarrow=False,
    yshift=-12,
    font=dict(color="#fde68a", size=11),
    bgcolor="rgba(17, 24, 39, 0.85)"
)

fig.update_layout(
    template="plotly_dark",
    height=560,
    margin=dict(l=15, r=20, t=30, b=20),
    xaxis_rangeslider_visible=False,
    xaxis=dict(
        title="Data (Histórico Recente → Janela até o Vencimento)",
        range=[plot_df.index[0], x_end_pad],
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.06)"
    ),
    yaxis=dict(
        title="Preço da Ação (R$)",
        range=[y_floor, y_ceil],
        tickprefix="R$ ",
        showgrid=True,
        gridcolor="rgba(255, 255, 255, 0.07)"
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0
    ),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 6. GLOSSÁRIO DETALHADO E CONTEXTUALIZADO COM OS PARÂMETROS ATUAIS
# ==============================================================================
intrinsic_now = max(0.0, current_price - strike_price) if is_call else max(0.0, strike_price - current_price)
extrinsic_now = max(0.0, float(premium) - intrinsic_now)
intrinsic_at_expiry = max(0.0, simulated_price - strike_price) if is_call else max(0.0, strike_price - simulated_price)
will_exercise = intrinsic_at_expiry > 0.0

if is_call and is_long:
    role_explanation = (
        f"Como **Titular (Comprador) de CALL** de **{clean_code}**, você pagou **R$ {premium:.2f}** por opção "
        f"(total de **R$ {total_cash_flow:,.2f}** para `{int(qty_options)}` opções) para ter o **direito** (não a obrigação) "
        f"de comprar a ação por **R$ {strike_price:.2f}** em `{expiry_dt.strftime('%d/%m/%Y')}`."
    )
elif is_call and not is_long:
    role_explanation = (
        f"Como **Lançador (Vendedor) de CALL** de **{clean_code}**, você recebeu antecipadamente **R$ {premium:.2f}** por opção "
        f"(crédito total de **R$ {total_cash_flow:,.2f}** para `{int(qty_options)}` opções) e assumiu a **obrigação** de entregar "
        f"a ação por **R$ {strike_price:.2f}** caso o comprador exerça no vencimento (`{expiry_dt.strftime('%d/%m/%Y')}`)."
    )
elif (not is_call) and is_long:
    role_explanation = (
        f"Como **Titular (Comprador) de PUT** de **{clean_code}**, você pagou **R$ {premium:.2f}** por opção "
        f"(total de **R$ {total_cash_flow:,.2f}** para `{int(qty_options)}` opções) para ter o **direito** (não a obrigação) "
        f"de vender a ação por **R$ {strike_price:.2f}** em `{expiry_dt.strftime('%d/%m/%Y')}` — lucrando com a queda ou protegendo sua carteira."
    )
else:
    role_explanation = (
        f"Como **Lançador (Vendedor) de PUT** de **{clean_code}**, você recebeu antecipadamente **R$ {premium:.2f}** por opção "
        f"(crédito total de **R$ {total_cash_flow:,.2f}** para `{int(qty_options)}` opções) e assumiu a **obrigação** de comprar "
        f"a ação por **R$ {strike_price:.2f}** caso ela feche abaixo do Strike no vencimento (`{expiry_dt.strftime('%d/%m/%Y')}`)."
    )

if will_exercise:
    exercise_explanation = (
        f"✅ **Haverá Exercício no Preço Simulado (R$ {simulated_price:.2f}):** Como no vencimento a opção tem "
        f"**Valor Intrínseco de R$ {intrinsic_at_expiry:.2f}** por unidade (`{'Preço > Strike' if is_call else 'Preço < Strike'}`), "
        f"ela termina **Dentro do Dinheiro (ITM)** e dá exercício."
    )
else:
    exercise_explanation = (
        f"💨 **A Opção 'Vira Pó' no Preço Simulado (R$ {simulated_price:.2f}):** Como no vencimento a ação simulada está "
        f"`{'abaixo ou igual ao' if is_call else 'acima ou igual ao'}` Strike (**R$ {strike_price:.2f}**), a opção expira sem valor (**R$ 0,00**). "
        f"{'O titular perde 100% do prêmio pago (R$ ' + f'{total_cash_flow:,.2f}' + ').' if is_long else 'O lançador embolsa 100% do prêmio recebido (R$ ' + f'{total_cash_flow:,.2f}' + ') sem ser exercido.'}"
    )

with st.expander("📖 Glossário Detalhado & Explicação dos Conceitos Aplicados à Sua Simulação", expanded=True):
    st.markdown(f"### 🎯 Resumo Didático da Sua Operação em **{clean_code}**")
    st.info(f"{role_explanation}\n\n{exercise_explanation}")

    g_col1, g_col2 = st.columns(2)

    with g_col1:
        st.markdown("#### 📌 1. Conceitos Estruturais (Seus Parâmetros)")
        st.markdown(
            f"- **Tipo: `{'CALL (Opção de Compra)' if is_call else 'PUT (Opção de Venda)'}`**\n"
            f"  - {'Valoriza quando a ação sobe. Usada para alavancar alta ou travar preço de compra.' if is_call else 'Valoriza quando a ação cai. Usada para lucrar na queda ou como seguro de carteira (hedge).'}\n"
            f"- **Ponta: `{'COMPRA (Titular)' if is_long else 'VENDA (Lançador)'}`**\n"
            f"  - {'Paga o prêmio na abertura (`Débito`), tem risco limitado ao valor pago e o tempo (Theta) joga contra.' if is_long else 'Recebe o prêmio na abertura (`Crédito`), tem ganho limitado ao prêmio recebido e o tempo (Theta) joga a favor.'}\n"
            f"- **Strike / Preço de Exercício (`R$ {strike_price:.2f}`):**\n"
            f"  - É o preço fixado no contrato. Comparado à cotação atual de **{clean_code}** (`R$ {current_price:.2f}`), esta opção está **{m_status}** (distância de `{moneyness_diff:+.2f}%`).\n"
            f"- **Classificação Moneyness (`ITM / ATM / OTM`):**\n"
            f"  - **ITM (*In The Money* / Dentro do Dinheiro):** Já possui valor imediato de exercício (`{'Cotação > Strike na Call' if is_call else 'Cotação < Strike na Put'}`).\n"
            f"  - **ATM (*At The Money* / No Dinheiro):** Strike muito próximo da cotação atual (`R$ {current_price:.2f}`). Maior liquidez na B3.\n"
            f"  - **OTM (*Out of The Money* / Fora do Dinheiro):** Ainda não daria exercício hoje (`{'Strike > Cotação na Call' if is_call else 'Strike < Cotação na Put'}`). Mais barata, composta 100% de expectativa (tempo)."
        )

    with g_col2:
        st.markdown("#### 💰 2. Decomposição do Prêmio, Empate e Black-Scholes")
        st.markdown(
            f"- **Prêmio Unitário (`R$ {premium:.2f}`) = Valor Intrínseco (`R$ {intrinsic_now:.2f}`) + Extrínseco (`R$ {extrinsic_now:.2f}`):**\n"
            f"  - **Valor Intrínseco (`R$ {intrinsic_now:.2f}`):** Quanto a opção já vale de forma real se exercida hoje.\n"
            f"  - **Valor Extrínseco / Tempo (`R$ {extrinsic_now:.2f}`):** É a 'gordura' ou expectativa pelos próximos **{days_to_expiry} dias úteis** até `{expiry_dt.strftime('%d/%m/%Y')}`. Esse valor decai todos os dias (**efeito Theta**) até zerar no vencimento.\n"
            f"- **Ponto de Empate / Breakeven (`R$ {breakeven:.2f}`):**\n"
            f"  - Calculado como `{'Strike (R$ ' + f'{strike_price:.2f}' + ') + Prêmio (R$ ' + f'{premium:.2f}' + ')' if is_call else 'Strike (R$ ' + f'{strike_price:.2f}' + ') - Prêmio (R$ ' + f'{premium:.2f}' + ')'}`.\n"
            f"  - É a linha amarela pontilhada que divide a **Zona Verde (Lucro)** da **Zona Vermelha (Prejuízo)** no gráfico. Para empatar, `{clean_code}` precisa **{be_dir_str} `{abs(breakeven_dist_pct):.2f}%`** até o vencimento.\n"
            f"- **Preço Teórico Black-Scholes (`R$ {bs_fair_premium:.2f}`):**\n"
            f"  - Calculado automaticamente usando a **Volatilidade Histórica Anualizada** de `{clean_code}` (`{hist_vol * 100:.1f}% a.a.`), o prazo (`{days_to_expiry}/252` anos) e a taxa de juros livre de risco (`{RISK_FREE_RATE * 100:.2f}% a.a.`). "
            f"{'O prêmio configurado está acima do teórico (opção mais cara / maior volatilidade implícita).' if premium > bs_fair_premium + 0.02 else ('O prêmio configurado está abaixo do teórico (opção descontada).' if premium < bs_fair_premium - 0.02 else 'O prêmio configurado está alinhado ao preço justo teórico.')}"
        )

