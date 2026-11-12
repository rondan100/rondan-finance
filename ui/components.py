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


def render_scanner_results(opportunities: list):
    """
    Renderiza o painel do Scanner de Oportunidades da B3 com destaques para ações
    em tendência de compra ou que estão em zonas estratégicas para ficar de olho.
    """
    if not opportunities:
        st.warning("Nenhum dado retornado no escaneamento. Tente novamente em instantes.")
        return

    # Contadores de categoria
    compras = [op for op in opportunities if op["categoria"] == "COMPRA"]
    olho = [op for op in opportunities if op["categoria"] == "OLHO"]
    outros = [op for op in opportunities if op["categoria"] not in ("COMPRA", "OLHO")]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🚀 Tendência de Compra Forte", f"{len(compras)} ativos", "Sinal Altista")
    with c2:
        st.metric("👀 Para Ficar de Olho", f"{len(olho)} ativos", "Reversão / Rompimento")
    with c3:
        st.metric("📊 Total Escaneado", f"{len(opportunities)} ativos", "B3 Top Líquidas")

    # Abas de navegação rápida
    tab_compras, tab_olho, tab_todas = st.tabs([
        f"🟢 Tendência de Compra ({len(compras)})",
        f"🟡 Interessante Ficar de Olho ({len(olho)})",
        f"📋 Todos os Ativos ({len(opportunities)})"
    ])

    def _render_cards(ops_subset):
        if not ops_subset:
            st.info("Nenhum ativo nesta categoria no momento.")
            return

        for op in ops_subset:
            delta_cor = "#10b981" if op['daily_pct'] >= 0 else "#ef4444"
            delta_5d_cor = "#10b981" if op['var5d'] >= 0 else "#ef4444"
            badge_cor = "#10b981" if "Compra" in op['sinal'] else ("#f59e0b" if "Olho" in op['sinal'] else "#6b7280")

            st.markdown(f"""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 4px solid {badge_cor}; border-radius: 8px; padding: 14px 18px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <span style="font-size: 1.15rem; font-weight: 700; color: #ffffff;">{op['ticker']}</span>
                        <span style="font-size: 0.95rem; color: #9ca3af; margin-left: 8px;">({op['company']})</span>
                        <span style="background-color: {badge_cor}22; color: {badge_cor}; border: 1px solid {badge_cor}; font-size: 0.8rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px; margin-left: 10px;">{op['sinal']}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.15rem; font-weight: 700; color: #f3f4f6;">R$ {op['price']:.2f}</span>
                        <span style="font-size: 0.9rem; font-weight: 600; color: {delta_cor}; margin-left: 10px;">Dia: {op['daily_pct']:+.2f}%</span>
                        <span style="font-size: 0.9rem; font-weight: 600; color: {delta_5d_cor}; margin-left: 10px;">5D: {op['var5d']:+.2f}%</span>
                    </div>
                </div>
                <div style="font-size: 0.88rem; color: #d1d5db; margin-top: 8px;">
                    💡 <b>Racional Técnico:</b> {op['motivo']} &nbsp;|&nbsp; <span style="color: #9ca3af;">MMA9: R$ {op['sma9']:.2f} • MMA21: R$ {op['sma21']:.2f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab_compras:
        _render_cards(compras)

    with tab_olho:
        _render_cards(olho)

    with tab_todas:
        _render_cards(opportunities)


def render_asset_qa_section(
    ticker: str,
    company_name: str,
    metrics: dict,
    news_items: list,
    current_analysis: dict,
    api_key: str,
    selected_model: str
):
    """
    Renderiza a barra de pesquisa e assistente interativo com IA sobre o ativo selecionado.
    Dispara imediatamente tanto ao clicar nos botões de sugestão rápida quanto ao digitar na barra de pesquisa.
    """
    st.markdown("---")
    st.subheader(f"💬 Pergunte à IA sobre {ticker}")
    st.caption(
        "Faça qualquer pergunta técnica ou fundamentalista. A IA responderá considerando "
        "automaticamente a **cotação atual, médias móveis do gráfico, últimas notícias e a tendência projetada**."
    )

    if not api_key or api_key == "sua_chave_aqui":
        st.info("💡 Insira sua API Key do Gemini na barra lateral para habilitar o assistente conversacional.")
        return

    # Chaves de controle na sessão para persistir histórico e gatilho de pergunta
    session_qa_key = f"qa_history_{ticker}"
    if session_qa_key not in st.session_state:
        st.session_state[session_qa_key] = []

    # Variável para capturar a pergunta que deve ser executada nesta rodada
    pergunta_a_executar = None

    # Sugestões rápidas de perguntas (chips clicáveis que já executam a consulta diretamente)
    st.markdown("<span style='font-size: 0.9rem; font-weight: 600; color: #9ca3af;'>⚡ Sugestões rápidas (clique para consultar imediatamente):</span>", unsafe_allow_html=True)
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    with col_s1:
        if st.button("📊 Comportamento das Médias", key=f"btn_sug_1_{ticker}", use_container_width=True):
            pergunta_a_executar = f"Como o cruzamento da MMA 9 e MMA 21 afeta a perspectiva de curto prazo de {ticker}?"

    with col_s2:
        if st.button("📰 Impacto das Notícias", key=f"btn_sug_2_{ticker}", use_container_width=True):
            pergunta_a_executar = f"Qual o impacto das notícias recentes no valuation e preço de {ticker}?"

    with col_s3:
        if st.button("💰 Dividendos & Preço", key=f"btn_sug_3_{ticker}", use_container_width=True):
            pergunta_a_executar = f"Vale a pena manter {ticker} na carteira visando dividendos e fluxo de caixa?"

    with col_s4:
        if st.button("⚠️ Principais Riscos", key=f"btn_sug_4_{ticker}", use_container_width=True):
            pergunta_a_executar = f"Quais são os maiores riscos macroeconômicos e setoriais para {ticker} agora?"

    # Campo de texto para pergunta livre (fora de form restritivo para permitir submissão fluida)
    col_input, col_submit = st.columns([4, 1])
    with col_input:
        texto_digitado = st.text_input(
            "Digite sua dúvida personalizada sobre o ativo:",
            placeholder=f"Ex: Vale a pena comprar {ticker} a R$ {metrics['current_price']:.2f}? Qual o suporte mais importante?",
            key=f"input_qa_{ticker}",
            label_visibility="collapsed"
        )
    with col_submit:
        btn_enviar = st.button("🔍 Consultar IA", key=f"btn_submit_qa_{ticker}", type="primary", use_container_width=True)

    if btn_enviar and texto_digitado.strip():
        pergunta_a_executar = texto_digitado.strip()

    # Executa a consulta se houver pergunta disparada (via chip ou campo de texto)
    if pergunta_a_executar:
        from services.ai_service import consultar_ia_sobre_ativo
        from services.news_service import format_news_for_prompt

        titulos_noticias = format_news_for_prompt(news_items, max_titles=5)
        tendencia_str = current_analysis.get("tendencia", "Em análise") if current_analysis else "Não consultada"

        with st.spinner(f"Analisando '{pergunta_a_executar[:45]}...' com {selected_model}..."):
            try:
                qa_res = consultar_ia_sobre_ativo(
                    ticker=ticker,
                    company_name=company_name,
                    pergunta_usuario=pergunta_a_executar,
                    dados_mercado_str=metrics.get("summary_line", ""),
                    titulos_noticias_str=titulos_noticias,
                    tendencia_atual_str=f"Tendência: {tendencia_str}",
                    api_key=api_key,
                    modelo_preferencial=selected_model
                )
                # Salva no histórico da sessão no topo
                st.session_state[session_qa_key].insert(0, {
                    "pergunta": pergunta_a_executar,
                    "resposta": qa_res["resposta"],
                    "modelo": qa_res["modelo_utilizado"]
                })
            except Exception as e:
                st.error(f"⚠️ Erro ao consultar a IA: {e}")

    # Exibe as respostas recentes salvas na sessão com formatação nativa rica do Streamlit
    if st.session_state[session_qa_key]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_hist_title, col_hist_clean = st.columns([4, 1])
        with col_hist_title:
            st.markdown("#### 📋 Respostas da IA para este ativo:")
        with col_hist_clean:
            if st.button("🗑️ Limpar Conversa", key=f"clean_qa_{ticker}", use_container_width=True):
                st.session_state[session_qa_key] = []
                st.rerun()

        for idx, item in enumerate(st.session_state[session_qa_key]):
            with st.container():
                st.markdown(f"""
                <div style="background-color: #1e293b; border-left: 4px solid #38bdf8; border-radius: 8px 8px 0 0; padding: 12px 16px; margin-top: 12px;">
                    <span style="font-weight: 700; color: #ffffff; font-size: 1.05rem;">❓ {item['pergunta']}</span>
                    <span style="float: right; background-color: #2563eb33; color: #60a5fa; border: 1px solid #2563eb; font-size: 0.75rem; font-weight: 600; padding: 2px 10px; border-radius: 9999px;">IA: {item['modelo']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Renderiza o conteúdo da resposta com Markdown puro do Streamlit (garante formatação perfeita)
                st.markdown(f"""
                <div style="background-color: #0f172a; border: 1px solid #334155; border-top: none; border-radius: 0 0 8px 8px; padding: 18px 20px; margin-bottom: 16px;">
                """, unsafe_allow_html=True)
                st.markdown(item['resposta'])
                st.markdown("</div>", unsafe_allow_html=True)


def render_footer():
    """
    Renderiza o rodapé institucional da aplicação.
    """
    st.markdown("""
    <div style="text-align: center; color: #6b7280; font-size: 0.85rem; margin-top: 40px; padding: 20px 0; border-top: 1px solid #1f2937;">
        Dashboard Financeiro B3 • Arquitetura Modular em Python & Streamlit • Motor de IA Google Gemini & Google AI Pro.<br>
        <i>Aviso: As análises têm caráter informativo e educacional e não representam recomendação formal de compra ou venda de ativos.</i>
    </div>
    """, unsafe_allow_html=True)

