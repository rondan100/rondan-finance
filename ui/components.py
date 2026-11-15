"""
Módulo de componentes visuais do Streamlit (métricas, containers de IA, notícias).
"""

import json
import streamlit as st


def render_top_metrics(metrics: dict, ticker: str, period: str):
    """
    Exibe os indicadores de topo: Preço atual, variação diária, médias móveis e extremos,
    com tooltips explicativos (help=) para facilitar a leitura em swing trade / momentum.
    """
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            label=f"Preço Atual ({ticker})",
            value=f"R$ {metrics['current_price']:.2f}",
            delta=f"{metrics['daily_delta_val']:+.2f} R$ ({metrics['daily_delta_pct']:+.2f}%)",
            help="Última cotação registrada no pregão da B3 e variação em relação ao fechamento anterior."
        )

    with m2:
        st.metric(
            label="MMA 9 períodos",
            value=f"R$ {metrics['sma9_val']:.2f}",
            delta=f"{(metrics['current_price'] - metrics['sma9_val']):+.2f} vs preço",
            delta_color="normal",
            help="Média Móvel Aritmética dos últimos 9 pregões (~2 semanas). Mede o impulso imediato de curtíssimo prazo."
        )

    with m3:
        st.metric(
            label="MMA 21 períodos",
            value=f"R$ {metrics['sma21_val']:.2f}",
            delta=f"{(metrics['current_price'] - metrics['sma21_val']):+.2f} vs preço",
            delta_color="normal",
            help="Média Móvel Aritmética dos últimos 21 pregões (~1 mês útil). Principal referência de suporte/resistência para swing trade."
        )

    with m4:
        st.metric(
            label=f"Faixa ({period})",
            value=f"R$ {metrics['max_period']:.2f}",
            delta=f"Mín: R$ {metrics['min_period']:.2f}",
            delta_color="off",
            help="Cotação máxima (topo) e mínima (fundo) atingidas pelo ativo dentro da janela temporal selecionada no gráfico."
        )


def render_canslim_card(canslim_data: dict):
    """
    Renderiza o card e checklist quantitativo CAN SLM focado em Swing Trade / Momentum,
    destacando o Regime de Mercado (M - Ibovespa MM21/MM50/MM200), o Veredito Operacional
    (trade_verdict), o placar dos 5 critérios da ação (C, A, N, S, L) e glossário completo.
    """
    if not canslim_data:
        return

    market_regime = canslim_data.get("market_regime", {}) or {}
    regime_status = market_regime.get("status", "ND")
    ibov_close = market_regime.get("ibov_close")
    mm21 = market_regime.get("mm21")
    mm50 = market_regime.get("mm50")
    mm200 = market_regime.get("mm200")
    trade_verdict = canslim_data.get("trade_verdict", "EVITAR")

    # 1. Banner de Destaque do Critério M (Direção do Mercado — MM21, MM50 e MM200)
    if regime_status == "ALTA_FORTE" and ibov_close is not None:
        st.success(
            f"🟢 **M — Direção do Mercado (IBOV em ALTA FORTE):** `^BVSP` aos **{ibov_close:,.0f} pts** | "
            f"**MM21:** {mm21:,.0f} • **MM50:** {mm50:,.0f} • **MM200:** {mm200:,.0f}. "
            f"*Tendência alinhada em todos os prazos — cenário ideal para rompimentos e swing trade.*"
        )
    elif regime_status == "RETOMADA_CURTO" and ibov_close is not None:
        st.info(
            f"🔵 **M — Direção do Mercado (IBOV em RETOMADA DE CURTO PRAZO):** `^BVSP` aos **{ibov_close:,.0f} pts** | "
            f"**MM21:** {mm21:,.0f} • **MM50:** {mm50:,.0f} • **MM200:** {mm200:,.0f}. "
            f"*Acima da MM21, mas ainda abaixo da MM50/MM200 — início de reversão, permite operações táticas de curto prazo com stop ajustado.*"
        )
    elif regime_status == "CAUTELA" and ibov_close is not None:
        st.warning(
            f"🟡 **M — Direção do Mercado (IBOV em ZONA DE CAUTELA):** `^BVSP` aos **{ibov_close:,.0f} pts** | "
            f"**MM21:** {mm21:,.0f} • **MM50:** {mm50:,.0f} • **MM200:** {mm200:,.0f}. "
            f"*Abaixo da MM21, mas sustentado pela MM50/MM200 — correção curta dentro de tendência maior; aguardar recuperar a MM21.*"
        )
    elif regime_status == "BAIXA" and ibov_close is not None:
        st.error(
            f"🔴 **M — Direção do Mercado (IBOV em TENDÊNCIA DE BAIXA):** `^BVSP` aos **{ibov_close:,.0f} pts** | "
            f"**MM21:** {mm21:,.0f} • **MM50:** {mm50:,.0f} • **MM200:** {mm200:,.0f}. "
            f"*Abaixo de todas as médias — tendência de baixa predominante; evitar compras de rompimento.*"
        )
    else:
        st.info("ℹ️ **M — Direção do Mercado (IBOV):** Dados históricos de 2 anos do `^BVSP` indisponíveis no momento.")

    st.caption("📏 *Legenda: **MM21** = média de 21 pregões (~1 mês) | **MM50** = ~2,5 meses | **MM200** = ~10 meses.*")

    # 2. Badge de Destaque do Veredito Operacional (Curto/Médio Prazo)
    if trade_verdict == "ENTRADA_FAVORAVEL":
        v_bg = "rgba(16, 185, 129, 0.14)"
        v_border = "#10b981"
        v_text = "🟢 Sinal Favorável de Momentum — Ativo forte alinhado com a direção do mercado."
    elif trade_verdict == "WATCHLIST":
        v_bg = "rgba(245, 158, 11, 0.14)"
        v_border = "#f59e0b"
        v_text = "🟡 Líder em Observação (Watchlist) — Bons fundamentos/força, mas aguarde o IBOV superar a MM21 ou explosão de volume."
    else:
        v_bg = "rgba(239, 68, 68, 0.14)"
        v_border = "#ef4444"
        v_text = "🔴 Fora do Padrão Momentum — Baixo alinhamento técnico/fundamentalista no momento."

    st.markdown(f"""
    <div style="background: {v_bg}; border: 1px solid {v_border}; border-left: 5px solid {v_border};
                border-radius: 8px; padding: 10px 14px; margin: 4px 0 8px 0; font-size: 0.94rem; font-weight: 600; color: #f9fafb;">
        🎯 <b>Veredito Operacional (Swing Trade / Momentum):</b> {v_text}
    </div>
    """, unsafe_allow_html=True)

    # 3. Placar dos 5 Critérios Específicos da Ação (C, A, N, S, L)
    details = canslim_data.get("criteria_details", [])
    strict_mode = canslim_data.get("strict_mode", False)
    mode_label = canslim_data.get("mode_label", "Estrito O'Neil" if strict_mode else "Calibrado B3")
    stock_details = [item for item in details if item.get("letter") in ("C", "A", "N", "S", "L")]
    stock_score = canslim_data.get("stock_score", sum(1 for i in stock_details if i.get("status") == "approved"))
    stock_valid = canslim_data.get(
        "stock_valid_criteria",
        sum(1 for i in stock_details if i.get("status") in ("approved", "rejected"))
    )

    if stock_valid > 0 and (stock_score / stock_valid) >= 0.65:
        border_color = "#10b981"
        badge_bg = "rgba(16, 185, 129, 0.18)"
        status_label = "Forte Alinhamento"
    elif stock_valid > 0 and (stock_score / stock_valid) >= 0.40:
        border_color = "#f59e0b"
        badge_bg = "rgba(245, 158, 11, 0.18)"
        status_label = "Alinhamento Moderado"
    else:
        border_color = "#ef4444"
        badge_bg = "rgba(239, 68, 68, 0.18)"
        status_label = "Baixo Alinhamento"

    pills_html = ""
    for item in stock_details:
        st_code = item.get("status", "na")
        letter = item.get("letter", "")
        if st_code == "approved":
            icon = "✅"
            p_color = "#10b981"
        elif st_code == "rejected":
            icon = "⚠️"
            p_color = "#f59e0b"
        else:
            icon = "➖"
            p_color = "#9ca3af"

        pills_html += (
            f'<span style="display:inline-flex;align-items:center;gap:4px;'
            f'background:rgba(255,255,255,0.05);border:1px solid {p_color}55;'
            f'border-radius:6px;padding:3px 8px;font-size:0.82rem;font-weight:600;color:#f3f4f6;">'
            f'{icon} {letter}</span> '
        )

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(31, 41, 55, 0.7) 100%);
                border: 1px solid #374151; border-left: 5px solid {border_color};
                border-radius: 10px; padding: 14px 18px; margin: 4px 0 10px 0;">
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 10px;">
                <span style="font-size: 1.05rem; font-weight: 700; color: #ffffff;">
                    📊 Score Quantitativo do Ativo (C-A-N-S-L): {stock_score}/{stock_valid} critérios atendidos
                </span>
                <span style="background: {badge_bg}; color: {border_color}; border: 1px solid {border_color};
                             padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: 700;">
                    {status_label}
                </span>
                <span style="background: rgba(59, 130, 246, 0.15); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.4);
                             padding: 2px 9px; border-radius: 999px; font-size: 0.76rem; font-weight: 600;">
                    ⚙️ {mode_label}
                </span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                {pills_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"Ver detalhes dos critérios CAN SLM — Modo: {mode_label} (Metas, Indicadores & Glossário)", expanded=False):
        if strict_mode:
            st.caption(
                "📘 **Modo Estrito Livro (O'Neil) Ativo:** "
                "**C** (LPA Trim. YoY > 20%) • **A** (CAGR Anual > 25% E ROE ≥ 17%) • "
                "**N** (Até 15% abaixo da Máx. 52s + Preço > MMA21) • **S** (Pico Vol 5d ≥ 1.25x MM20 em dia de alta) • "
                "**L** (Força Relativa / RS 63 pregões > IBOV)."
            )
        else:
            st.caption(
                "🇧🇷 **Modo Calibrado B3 Ativo:** "
                "**C** (LPA Trim. YoY > 12%) • **A** ((CAGR > 15% e ROE ≥ 14%) ou (ROE ≥ 17% e CAGR > 5%)) • "
                "**N** (Até 20% abaixo da Máx. 52s + Preço > MMA21) • **S** (Pico Vol 5d ≥ 1.25x MM20 em dia de alta) • "
                "**L** (Força Relativa / RS 63 pregões > IBOV)."
            )
        cols = st.columns(2)
        for idx, item in enumerate(details):
            st_code = item.get("status", "na")
            if st_code == "approved":
                icon_str = "✅"
                accent = "#10b981"
            elif st_code == "rejected":
                icon_str = "⚠️"
                accent = "#f59e0b"
            else:
                icon_str = "➖ N/D"
                accent = "#6b7280"

            with cols[idx % 2]:
                st.markdown(f"""
                <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748;
                            border-left: 4px solid {accent}; border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="font-weight: 700; color: #ffffff; font-size: 0.95rem;">
                            {icon_str} &nbsp;<b>{item.get('letter')}</b> — {item.get('name')}
                        </span>
                        <span style="font-weight: 700; color: {accent}; font-size: 0.9rem; background: rgba(0,0,0,0.25);
                                     padding: 2px 8px; border-radius: 6px;">
                            {item.get('value', 'N/D')}
                        </span>
                    </div>
                    <div style="font-size: 0.84rem; color: #9ca3af; margin-top: 6px; line-height: 1.4;">
                        {item.get('description', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📖 Glossário Rápido dos Indicadores")
        st.markdown(
            "- **MM21 / MM50 / MM200:** Médias Móveis de 21 pregões (~1 mês), 50 pregões (~2,5 meses) e 200 pregões (~10 meses). Preço acima da média indica força compradora no respectivo prazo.\n"
            "- **YoY (Year-over-Year):** Comparação do resultado trimestral atual contra o mesmo trimestre do ano anterior (elimina efeitos sazonais).\n"
            "- **CAGR:** Taxa de Crescimento Anual Composta dos lucros nos últimos anos disponíveis.\n"
            "- **ROE (Return on Equity):** Retorno sobre o Patrimônio Líquido — mede a eficiência da empresa em gerar lucro com o capital próprio.\n"
            "- **Volume Relativo (S):** Volume financeiro negociado comparado à média dos últimos 20 pregões (valores acima de 1,25x indicam entrada forte de compradores/institucionais).\n"
            "- **Força Relativa / RS (L):** Desempenho percentual da ação comparado ao Ibovespa nos últimos 63 pregões (~3 meses)."
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
    Renderiza o painel do Scanner de Oportunidades da B3 combinando tendência técnica
    (MMA 9/21) e o Score Quantitativo CAN SLM (C-A-N-S-L) de cada ativo conforme o
    Perfil de Rigor selecionado ('Calibrado B3' ou 'Estrito Livro O'Neil').
    """
    if not opportunities:
        st.warning("Nenhum dado retornado no escaneamento. Tente novamente em instantes.")
        return

    first_op = opportunities[0]
    strict_mode = first_op.get("strict_mode", False)
    mode_label = first_op.get("mode_label", "Estrito O'Neil" if strict_mode else "Calibrado B3")

    if strict_mode:
        st.caption(
            "📘 **Perfil de Rigor no Radar: Estrito Livro (O'Neil)** — "
            "**C** (LPA YoY > 20%) • **A** (CAGR > 25% E ROE ≥ 17%) • "
            "**N** (Topo 52s ≤ 15%) • **S** (Pico Vol 5d ≥ 1.25x MM20 + Alta) • **L** (Força Relativa 3M > IBOV)"
        )
    else:
        st.caption(
            "🇧🇷 **Perfil de Rigor no Radar: Calibrado B3** — "
            "**C** (LPA YoY > 12%) • **A** ((CAGR > 15% e ROE ≥ 14%) ou (ROE ≥ 17% e CAGR > 5%)) • "
            "**N** (Topo 52s ≤ 20%) • **S** (Pico Vol 5d ≥ 1.25x MM20 + Alta) • **L** (Força Relativa 3M > IBOV)"
        )

    # Contadores de categoria e líderes CAN SLM
    compras = [op for op in opportunities if op["categoria"] == "COMPRA"]
    olho = [op for op in opportunities if op["categoria"] == "OLHO"]
    top_canslim = sorted(
        [op for op in opportunities if op.get("canslim_score", 0) >= 3 or op.get("canslim_ratio", 0) >= 0.60],
        key=lambda x: (x.get("canslim_score", 0), x.get("canslim_ratio", 0), x.get("score", 0)),
        reverse=True
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🚀 Tendência de Compra", f"{len(compras)} ativos", f"MMA 9/21 + {mode_label}")
    with c2:
        st.metric(f"🏆 Líderes CAN SLM (≥ 3)", f"{len(top_canslim)} ativos", f"Modo: {mode_label}")
    with c3:
        st.metric("👀 Para Ficar de Olho", f"{len(olho)} ativos", "Reversão / Pullback")
    with c4:
        st.metric("📊 Total Escaneado", f"{len(opportunities)} ativos", "B3 Liquidez")

    # Abas de navegação rápida
    tab_compras, tab_canslim, tab_olho, tab_todas = st.tabs([
        f"🟢 Tendência de Compra ({len(compras)})",
        f"🏆 Top Score CAN SLM ({len(top_canslim)})",
        f"🟡 Interessante Ficar de Olho ({len(olho)})",
        f"📋 Todos os Ativos ({len(opportunities)})"
    ])

    def _render_cards(ops_subset, tab_key="radar"):
        if not ops_subset:
            st.info("Nenhum ativo nesta categoria no momento.")
            return

        from config import PopularB3Asset

        for op in ops_subset:
            delta_cor = "#10b981" if op['daily_pct'] >= 0 else "#ef4444"
            delta_5d_cor = "#10b981" if op['var5d'] >= 0 else "#ef4444"
            badge_cor = "#10b981" if "Compra" in op['sinal'] else ("#f59e0b" if "Olho" in op['sinal'] else "#6b7280")

            # Dados do Score Quantitativo CAN SLM (C-A-N-S-L)
            cs_score = op.get("canslim_score", 0)
            cs_valid = op.get("canslim_valid", 5)
            cs_ratio = op.get("canslim_ratio", 0.0)
            cs_details = op.get("canslim_details", [])

            if cs_valid > 0 and cs_ratio >= 0.60:
                cs_cor = "#10b981"
            elif cs_valid > 0 and cs_ratio >= 0.40:
                cs_cor = "#f59e0b"
            else:
                cs_cor = "#9ca3af"

            # Mini pílulas C-A-N-S-L para o card do Radar
            cs_pills = ""
            for item in cs_details:
                st_code = item.get("status", "na")
                letter = item.get("letter", "")
                ic = "✅" if st_code == "approved" else ("⚠️" if st_code == "rejected" else "➖")
                cs_pills += (
                    f'<span style="font-size:0.75rem;background:rgba(255,255,255,0.05);'
                    f'border:1px solid #374151;border-radius:4px;padding:1px 5px;margin-right:4px;color:#e5e7eb;">'
                    f'{ic}{letter}</span>'
                )

            col_card_info, col_card_btn = st.columns([5, 1.2])

            with col_card_info:
                st.markdown(f"""
                <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 4px solid {badge_cor}; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 6px;">
                            <span style="font-size: 1.15rem; font-weight: 700; color: #ffffff;">{op['ticker']}</span>
                            <span style="font-size: 0.92rem; color: #9ca3af;">({op['company']})</span>
                            <span style="background-color: {badge_cor}22; color: {badge_cor}; border: 1px solid {badge_cor}; font-size: 0.78rem; font-weight: 600; padding: 2px 8px; border-radius: 9999px;">{op['sinal']}</span>
                            <span style="background-color: {cs_cor}22; color: {cs_cor}; border: 1px solid {cs_cor}; font-size: 0.78rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">📊 CAN SLM ({op.get('mode_label', mode_label)}): {cs_score}/{cs_valid}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="font-size: 1.15rem; font-weight: 700; color: #f3f4f6;">R$ {op['price']:.2f}</span>
                            <span style="font-size: 0.9rem; font-weight: 600; color: {delta_cor}; margin-left: 10px;">Dia: {op['daily_pct']:+.2f}%</span>
                            <span style="font-size: 0.9rem; font-weight: 600; color: {delta_5d_cor}; margin-left: 10px;">5D: {op['var5d']:+.2f}%</span>
                        </div>
                    </div>
                    <div style="font-size: 0.86rem; color: #d1d5db; margin-top: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div>
                            💡 <b>Racional:</b> {op['motivo']} &nbsp;|&nbsp; <span style="color: #9ca3af;">MMA9: R$ {op['sma9']:.2f} • MMA21: R$ {op['sma21']:.2f}</span>
                        </div>
                        <div>
                            {cs_pills}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_card_btn:
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                btn_clicado = st.button(
                    "📊 Analisar",
                    key=f"btn_radar_sel_{op['ticker']}_{tab_key}",
                    use_container_width=True,
                    help=f"Carregar {op['ticker']} ({op['company']}) no Dashboard Principal"
                )
                if btn_clicado:
                    target_enum = None
                    for asset in PopularB3Asset:
                        # Compara o código com ou sem .SA
                        asset_code = asset.value.split(" - ")[0].strip()
                        if op['ticker'] == asset_code or op['ticker'].replace(".SA", "") == asset_code.replace(".SA", ""):
                            target_enum = asset.value
                            break
                    if not target_enum:
                        target_enum = op['ticker']

                    # Define a intenção de troca de ativo para o topo do ciclo de vida do Streamlit
                    st.session_state["target_asset_to_select"] = target_enum
                    # Fecha o painel do radar para que o usuário veja diretamente o dashboard principal
                    st.session_state["radar_expander_open"] = False
                    st.toast(f"✅ {op['ticker']} carregado no Dashboard Principal!", icon="🚀")
                    st.rerun()

    with tab_compras:
        _render_cards(compras, tab_key="compras")

    with tab_canslim:
        _render_cards(top_canslim, tab_key="canslim")

    with tab_olho:
        _render_cards(olho, tab_key="olho")

    with tab_todas:
        _render_cards(opportunities, tab_key="todas")


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
        from services.ai_service import stream_ia_sobre_ativo
        from services.news_service import format_news_for_prompt

        titulos_noticias = format_news_for_prompt(news_items, max_titles=2)
        tendencia_str = current_analysis.get("tendencia", "Em análise") if current_analysis else "Não consultada"

        # Painel de exibição imediata com digitação em tempo real (Streaming)
        st.markdown(f"""
        <div style="background-color: #1e293b; border-left: 4px solid #38bdf8; border-radius: 8px 8px 0 0; padding: 12px 16px; margin-top: 16px;">
            <span style="font-weight: 700; color: #ffffff; font-size: 1.05rem;">❓ {pergunta_a_executar}</span>
            <span style="float: right; background-color: #10b98122; color: #10b981; border: 1px solid #10b981; font-size: 0.75rem; font-weight: 600; padding: 2px 10px; border-radius: 9999px;">⚡ Tempo Real (Streaming)</span>
        </div>
        """, unsafe_allow_html=True)

        resp_container = st.container()
        with resp_container:
            st.markdown("""
            <div style="background-color: #0f172a; border: 1px solid #334155; border-top: none; border-radius: 0 0 8px 8px; padding: 18px 20px; margin-bottom: 16px;">
            """, unsafe_allow_html=True)

            try:
                # Transmite palavra a palavra em tempo real (primeira palavra em ~300ms)
                gerador_stream = stream_ia_sobre_ativo(
                    ticker=ticker,
                    company_name=company_name,
                    pergunta_usuario=pergunta_a_executar,
                    dados_mercado_str=metrics.get("summary_line", ""),
                    titulos_noticias_str=titulos_noticias,
                    tendencia_atual_str=f"Tendência: {tendencia_str}",
                    api_key=api_key,
                    modelo_preferencial=selected_model
                )
                resposta_completa = st.write_stream(gerador_stream)
                st.markdown("</div>", unsafe_allow_html=True)

                # Salva no histórico da sessão evitando duplicatas consecutivas
                if not st.session_state[session_qa_key] or st.session_state[session_qa_key][0]["pergunta"] != pergunta_a_executar:
                    st.session_state[session_qa_key].insert(0, {
                        "pergunta": pergunta_a_executar,
                        "resposta": resposta_completa,
                        "modelo": selected_model
                    })
            except Exception as e:
                st.markdown("</div>", unsafe_allow_html=True)
                st.error(f"⚠️ Erro ao transmitir resposta da IA: {e}")

    # Exibe as respostas recentes salvas na sessão (exceto a que acabou de ser transmitida acima)
    respostas_anteriores = st.session_state[session_qa_key][1:] if pergunta_a_executar else st.session_state[session_qa_key]
    if respostas_anteriores:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        col_hist_title, col_hist_clean = st.columns([4, 1])
        with col_hist_title:
            st.markdown("#### 📋 Respostas da IA para este ativo:")
        with col_hist_clean:
            if st.button("🗑️ Limpar Conversa", key=f"clean_qa_{ticker}", use_container_width=True):
                st.session_state[session_qa_key] = []
                st.rerun()

        for idx, item in enumerate(respostas_anteriores):
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

