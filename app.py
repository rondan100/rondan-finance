"""
Dashboard Financeiro B3 & Análise com IA (Google Gemini)
Ponto de entrada principal da aplicação Streamlit.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Módulos internos padronizados
from config import DEFAULT_TICKER, DEFAULT_PERIOD, PERIOD_MAPPING, GEMINI_MODELS, GEMINI_MODEL_RPD, PopularB3Asset
from services.market_data import (
    normalize_ticker,
    get_search_name,
    fetch_stock_data,
    calculate_market_metrics,
    scan_b3_market_opportunities
)
from services.news_service import fetch_google_news, format_news_for_prompt
from services.ai_service import gerar_analise_cached, get_available_models
from ui.styles import apply_custom_css
from ui.charts import create_candlestick_chart
from ui.components import (
    render_top_metrics,
    render_ai_card,
    render_reasons_and_variables,
    render_news_expander,
    render_scanner_results,
    render_asset_qa_section,
    render_footer
)

# Carrega credenciais do arquivo .env
load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Financeiro B3 | Análise IA",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar estilo visual moderno
apply_custom_css()

# ==============================================================================
# BARRA LATERAL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/bullish.png", width=64)
    st.title("Parâmetros do Ativo")
    st.markdown("Selecione uma ação da B3 e configure o período para análise técnica e diagnósticos com IA.")
    
    # Campo de seleção da ação B3 via Enum com os assets mais populares
    selected_enum_val = st.selectbox(
        "Ação da B3 (Ativos Populares):",
        options=[asset.value for asset in PopularB3Asset],
        index=0,  # Padrão: PETR4.SA - Petrobras (PN)
        help="Escolha diretamente entre as ações mais negociadas da B3 ou selecione 'OUTRO' para digitar qualquer ticker."
    )
    
    if selected_enum_val == PopularB3Asset.OUTRO.value:
        user_ticker = st.text_input(
            "Digite o Código do Ticker (B3):",
            value="PETR4.SA",
            placeholder="Ex: SAPR11.SA, TAEE11.SA, KLBN11.SA...",
            help="Informe o código do ticker com ou sem .SA."
        )
        ticker_normalized = normalize_ticker(user_ticker)
        asset_display_name = ticker_normalized
    else:
        # Extrai o código do ticker antes do hífen (ex: 'PETR4.SA - Petrobras (PN)' -> 'PETR4.SA')
        user_ticker = selected_enum_val.split(" - ")[0].strip()
        ticker_normalized = normalize_ticker(user_ticker)
        asset_display_name = selected_enum_val
    
    # Seletor de período do gráfico (1m, 3m, 6m, 1y)
    period_selected = st.selectbox(
        "Período do Histórico:",
        options=list(PERIOD_MAPPING.keys()),
        index=list(PERIOD_MAPPING.keys()).index(DEFAULT_PERIOD),
        help="Período das cotações no gráfico e para o resumo de mercado."
    )
    
    st.markdown("---")
    
    # Configuração da Chave da API do Gemini
    env_gemini_key = os.getenv("GEMINI_API_KEY", "")
    st.subheader("🔑 Motor de IA Gemini")
    
    gemini_key_input = st.text_input(
        "Gemini API Key:",
        value=env_gemini_key if env_gemini_key and env_gemini_key != "sua_chave_aqui" else "",
        type="password",
        placeholder="Cole sua API Key aqui...",
        help="Obtenha gratuitamente em https://aistudio.google.com/"
    )
    active_api_key = gemini_key_input.strip() if gemini_key_input.strip() else env_gemini_key

    # Descoberta dinâmica de modelos disponíveis para a chave do usuário (incluindo Pro e Argon)
    available_models = get_available_models(active_api_key)
    model_options = available_models + ["Outro (digitar modelo)"] if "Outro (digitar modelo)" not in available_models else available_models

    model_choice = st.selectbox(
        "Modelo do Gemini / Google AI Pro:",
        options=model_options,
        index=0,
        help="Modelos da família Gemini e Google AI Studio Pro (ex: gemini-1.5-pro, gemini-3.8-pro, argon)."
    )

    if model_choice == "Outro (digitar modelo)":
        custom_model = st.text_input(
            "Nome do modelo:",
            value="argon",
            placeholder="Ex: argon, gemini-exp-1206...",
            help="Informe o identificador exato do modelo habilitado na sua conta Google AI."
        )
        selected_model = custom_model.strip() if custom_model.strip() else "gemini-3.5-flash-lite"
    else:
        selected_model = model_choice

    rpd_desc = GEMINI_MODEL_RPD.get(selected_model, "Google AI Pro / Custom")
    st.caption(f"⚡ **Capacidade:** `{selected_model}` ({rpd_desc})")
    
    st.markdown("---")
    
    # Botão para recarregar dados e limpar cache
    btn_reload = st.button("🔄 Atualizar Análise (Limpar Cache)", use_container_width=True)
    if btn_reload:
        st.cache_data.clear()
        if "ai_analysis_data" in st.session_state:
            st.session_state["ai_analysis_data"] = {}
        st.rerun()


# ==============================================================================
# FLUXO PRINCIPAL DA APLICAÇÃO
# ==============================================================================

# Cabeçalho
st.title("📊 Dashboard Financeiro B3 & Análise com IA")
st.markdown(f"Análise técnica quantitativa e qualitativa em tempo real para **{asset_display_name}**.")

# 1. Coleta de dados via yfinance
with st.spinner(f"Coletando cotações para {ticker_normalized}..."):
    hist_data, ticker_info = fetch_stock_data(ticker_normalized, period_selected)

if hist_data is None or hist_data.empty:
    st.error(f"❌ Não foi possível carregar os dados para o ticker **{ticker_normalized}**. Verifique se o código está correto (ex: PETR4.SA, VALE3.SA).")
    st.stop()

# Nome da empresa para busca de notícias
company_name = get_search_name(ticker_normalized, ticker_info)

# 2. Coleta de Notícias via Google News RSS
with st.spinner(f"Extraindo notícias recentes sobre {company_name}..."):
    news_items = fetch_google_news(company_name)

# 3. Métricas Técnicas no Topo
metrics = calculate_market_metrics(hist_data)
render_top_metrics(metrics, ticker_normalized, period_selected)

st.markdown("---")

# ==============================================================================
# RADAR B3 / SCANNER DE TENDÊNCIA DE COMPRA E OPORTUNIDADES
# ==============================================================================
with st.expander("🎯 Radar B3: Escanear Ações com Tendência de Compra / Ficar de Olho", expanded=False):
    st.markdown(
        "Identifique automaticamente quais das ações mais negociadas da Bolsa Brasileira (**B3**) "
        "estão em **forte tendência de alta / sinal de compra** (Preço > MMA 9 > MMA 21) ou em zonas de "
        "**reversão/rompimento altista** para acompanhar de perto."
    )
    col_scan_btn, col_scan_info = st.columns([1, 2])
    with col_scan_btn:
        btn_scan_radar = st.button("🔍 Escanear Mercado B3 Agora", type="secondary", use_container_width=True)
    with col_scan_info:
        st.caption("⚡ Análise técnica quantitativa baseada em médias móveis (MMA 9 e 21), variações e momentum dos ativos populares.")

    if btn_scan_radar:
        with st.spinner("Escaneando e ranqueando oportunidades nos principais ativos da B3..."):
            st.session_state["b3_scan_results"] = scan_b3_market_opportunities()

    if "b3_scan_results" in st.session_state and st.session_state["b3_scan_results"]:
        render_scanner_results(st.session_state["b3_scan_results"])

st.markdown("---")

# Inicializar armazenamento da análise na sessão
if "ai_analysis_data" not in st.session_state:
    st.session_state["ai_analysis_data"] = {}

analysis_key = f"{ticker_normalized}_{period_selected}_{selected_model}"
current_analysis = st.session_state["ai_analysis_data"].get(analysis_key)

# ==============================================================================
# SEÇÃO DO MOTOR DE IA (GOOGLE GEMINI - DISPARO POR BOTÃO)
# ==============================================================================
st.subheader("🤖 Diagnóstico de IA | Tendência de Mercado")

if not active_api_key or active_api_key == "sua_chave_aqui":
    st.info("💡 **Dica:** Para ativar a análise preditiva por Inteligência Artificial, informe sua **GEMINI_API_KEY** no arquivo `.env` ou insira-a no campo correspondente na barra lateral.")
else:
    col_btn, col_msg = st.columns([1, 2])
    with col_btn:
        btn_disparar_ia = st.button("⚡ Gerar Diagnóstico com IA", type="primary", use_container_width=True)
    with col_msg:
        rpd = GEMINI_MODEL_RPD.get(selected_model, "?")
        st.caption(f"Modelo: `{selected_model}` ({rpd} consultas/dia no nível gratuito). A IA só é consultada quando você clica no botão.")

    if btn_disparar_ia:
        titulos_noticias = format_news_for_prompt(news_items)
        with st.spinner(f"Processando diagnóstico com {selected_model}..."):
            try:
                ai_result = gerar_analise_cached(
                    ticker=f"{ticker_normalized} ({company_name})",
                    dados_mercado_str=metrics["summary_line"],
                    titulos_noticias_str=titulos_noticias,
                    api_key=active_api_key,
                    modelo_preferencial=selected_model
                )
                st.session_state["ai_analysis_data"][analysis_key] = ai_result
                current_analysis = ai_result
            except Exception as err:
                st.error(f"⚠️ Erro ao analisar: {err}")

    # Exibe o diagnóstico gerado e mantido na sessão para o ativo atual
    if current_analysis:
        render_ai_card(current_analysis)
        render_reasons_and_variables(
            motivos=current_analysis.get("principais_motivos", []),
            variaveis=current_analysis.get("variaveis_chave", []),
            ai_result=current_analysis,
            ticker=ticker_normalized
        )
    elif not btn_disparar_ia:
        st.info(f"💡 Para gerar o diagnóstico inteligente de **{ticker_normalized}**, clique no botão **⚡ Gerar Diagnóstico com IA** acima.")

st.markdown("---")

# ==============================================================================
# GRÁFICO INTERATIVO CANDLESTICK
# ==============================================================================
st.subheader("📈 Análise Gráfica Interativa")
fig_candle = create_candlestick_chart(hist_data, ticker_normalized, current_price=metrics['current_price'])
st.plotly_chart(fig_candle, use_container_width=True)

# ==============================================================================
# SEÇÃO SANFONADA DE NOTÍCIAS (EXPANDER)
# ==============================================================================
render_news_expander(news_items, company_name)

# ==============================================================================
# ASSISTENTE INTERATIVO DE CONSULTA COM IA (CONTEXTO DO ATIVO)
# ==============================================================================
render_asset_qa_section(
    ticker=ticker_normalized,
    company_name=company_name,
    metrics=metrics,
    news_items=news_items,
    current_analysis=current_analysis,
    api_key=active_api_key,
    selected_model=selected_model
)

# Rodapé
render_footer()
