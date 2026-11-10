"""
Módulo de componentes visuais do Streamlit (métricas, containers de IA, notícias).
"""

import json
import streamlit as st


def render_top_metrics(metrics: dict, ticker: str, period: str):
    """
    Exibe os indicadores de topo: Preço atual, variação diária, médias móveis e extremos.
    """
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            label=f"Preço Atual ({ticker})",
            value=f"R$ {metrics['current_price']:.2f}",
            delta=f"{metrics['daily_delta_val']:+.2f} R$ ({metrics['daily_delta_pct']:+.2f}%)"
        )

    with m2:
        st.metric(
            label="MMA 9 períodos",
            value=f"R$ {metrics['sma9_val']:.2f}",
            delta=f"{(metrics['current_price'] - metrics['sma9_val']):+.2f} vs preço",
            delta_color="normal"
        )

    with m3:
        st.metric(
            label="MMA 21 períodos",
            value=f"R$ {metrics['sma21_val']:.2f}",
            delta=f"{(metrics['current_price'] - metrics['sma21_val']):+.2f} vs preço",
            delta_color="normal"
        )

    with m4:
        st.metric(
            label=f"Faixa ({period})",
            value=f"R$ {metrics['max_period']:.2f}",
            delta=f"Mín: R$ {metrics['min_period']:.2f}",
            delta_color="off"
        )


def render_ai_card(ai_result: dict):
    """
    Renderiza o card de IA estilizado de acordo com a tendência (ALTA, BAIXA, NEUTRA).
    """
    tendencia = str(ai_result.get("tendencia", "NEUTRA")).upper().strip()
    
    # Tratamento flexível de confiança (confianca_pct ou confianca)
    confianca_val = ai_result.get("confianca_pct", ai_result.get("confianca", "N/D"))
    if isinstance(confianca_val, (int, float)):
        confianca = f"{confianca_val}%"
    else:
        confianca = str(confianca_val)

    resumo = ai_result.get("resumo_executivo", "Resumo indisponível no momento.")
    modelo_usado = ai_result.get("modelo_utilizado", "gemini-3.5-flash-lite")

    # Identificação visual
    if "ALTA" in tendencia:
        card_class = "ai-card-alta"
        badge_class = "badge-alta"
        icon = "🟢"
    elif "BAIXA" in tendencia:
        card_class = "ai-card-baixa"
        badge_class = "badge-baixa"
        icon = "🔴"
    else:
        card_class = "ai-card-neutra"
        badge_class = "badge-neutra"
        icon = "🟡"

    st.markdown(f"""
    <div class="{card_class}">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center;">
                <span style="font-size: 1.6rem; margin-right: 10px;">{icon}</span>
                <span style="font-size: 1.4rem; font-weight: 700; color: #ffffff;">Tendência Projetada:</span>
                <span class="badge-pill {badge_class}" style="margin-left: 12px;">{tendencia}</span>
                <span class="badge-model">IA: {modelo_usado}</span>
            </div>
            <div>
                <span style="font-size: 0.95rem; color: #9ca3af; font-weight: 600;">Grau de Confiança:</span>
                <span class="badge-pill badge-confianca">{confianca}</span>
            </div>
        </div>
        <div style="font-size: 1.1rem; line-height: 1.6; color: #e5e7eb; margin-bottom: 8px; font-weight: 500;">
            {resumo}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_reasons_and_variables(motivos: list, variaveis: list, ai_result: dict = None, ticker: str = ""):
    """
    Exibe em duas colunas formatadas os motivos e as variáveis macroeconômicas de impacto,
    além de disponibilizar o botão de exportação da análise.
    """
    col_motivos, col_variaveis = st.columns(2)

    with col_motivos:
        st.markdown("### 🎯 Principais Motivos da Projeção")
        if motivos and isinstance(motivos, list):
            for idx, motivo in enumerate(motivos, 1):
                st.markdown(f"""
                <div class="reason-item">
                    <b>{idx}.</b> {motivo}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("Nenhum motivo detalhado retornado.")

    with col_variaveis:
        st.markdown("### 🌐 Variáveis-Chave de Impacto Macro")
        if variaveis and isinstance(variaveis, list):
            for var in variaveis:
                st.markdown(f"""
                <div class="macro-item">
                    ⚡ {var}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("Nenhuma variável macro listada.")

    # Botão opcional para exportar a análise completa
    if ai_result:
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        report_json = json.dumps(ai_result, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Exportar Diagnóstico Completo da IA (JSON)",
            data=report_json,
            file_name=f"diagnostico_ia_{ticker.replace('.', '_')}.json",
            mime="application/json",
            use_container_width=True
        )


def render_news_expander(news_items: list, company_name: str):
    """
    Renderiza a seção sanfonada com as notícias originais extraídas e links diretos.
    """
    with st.expander(f"📰 Notícias Recentes do Google News ({len(news_items)} notícias sobre {company_name})", expanded=False):
        if not news_items:
            st.write("Nenhuma notícia recente encontrada no feed do Google News.")
        else:
            for item in news_items:
                st.markdown(f"""
                <div class="news-card">
                    <div style="font-size: 1rem; font-weight: 600; margin-bottom: 6px;">
                        <a href="{item['link']}" target="_blank" style="color: #60a5fa; text-decoration: none;">
                            🔗 {item['title']}
                        </a>
                    </div>
                    <div style="font-size: 0.85rem; color: #9ca3af;">
                        📰 <b>{item['source']}</b> &nbsp;|&nbsp; 🕒 {item['published']}
                    </div>
                </div>
                """, unsafe_allow_html=True)


def render_footer():
    """
    Renderiza o rodapé institucional da aplicação.
    """
    st.markdown("""
    <div style="text-align: center; color: #6b7280; font-size: 0.85rem; margin-top: 40px; padding: 20px 0; border-top: 1px solid #1f2937;">
        Dashboard Financeiro B3 • Arquitetura Modular em Python & Streamlit • Motor de IA Google Gemini (gemini-3.5-flash-lite).<br>
        <i>Aviso: As análises têm caráter informativo e educacional e não representam recomendação formal de compra ou venda de ativos.</i>
    </div>
    """, unsafe_allow_html=True)

