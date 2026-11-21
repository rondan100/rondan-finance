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


def render_share_calculator_tab(ticker: str, company_name: str, metrics: dict, ticker_info: dict = None):
    """
    Renderiza a aba de Calculadora de Ações <-> Valor Investido (Ida e Volta),
    considerando lote padrão (100 ações), mercado fracionário, troco e dividend yield estimado.
    """
    current_price = float(metrics.get("current_price", 0.0))
    if current_price <= 0:
        st.warning("Cotação atual indisponível para realizar o cálculo.")
        return

    info = ticker_info if isinstance(ticker_info, dict) else {}
    div_yield = info.get("dividendYield")
    has_dy = div_yield is not None and isinstance(div_yield, (int, float)) and div_yield > 0
    # yfinance às vezes retorna dividendYield como decimal (0.08) ou percentual (8.0)
    if has_dy:
        dy_decimal = float(div_yield) / 100.0 if float(div_yield) > 1.0 else float(div_yield)
    else:
        dy_decimal = 0.0

    clean_ticker = ticker.replace(".SA", "")

    st.subheader(f"🧮 Simulador de Posição & Conversor: {clean_ticker} ({company_name})")
    st.markdown(
        f"Descubra instantaneamente **quantas ações de `{clean_ticker}` você consegue comprar** com um determinado valor "
        f"ou **quanto custa acumular uma quantidade específica de ações**, com base na cotação atual de **R$ {current_price:,.2f}**."
    )

    # Controle de preço de referência (permite usar cotação atual ou simular outro preço-alvo)
    col_ref1, col_ref2 = st.columns([1.2, 2.8])
    with col_ref1:
        custom_price = st.number_input(
            f"Cotação de Referência ({clean_ticker}) [R$]:",
            min_value=0.01,
            value=round(current_price, 2),
            step=0.10,
            format="%.2f",
            key=f"calc_ref_price_{ticker}",
            help="Por padrão utiliza a última cotação da B3, mas você pode alterar para simular um preço-alvo de compra ou venda."
        )
    with col_ref2:
        diff_ref_pct = ((custom_price - current_price) / current_price) * 100.0 if current_price else 0.0
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if abs(custom_price - current_price) < 0.005:
            st.caption(
                f"📌 Usando a **cotação atual de mercado** (**R$ {current_price:.2f}**). "
                f"1 Lote Padrão (100 ações) = **R$ {current_price * 100:,.2f}**."
            )
        else:
            st.caption(
                f"🎯 Simulando com preço personalizado de **R$ {custom_price:.2f}** "
                f"(**{diff_ref_pct:+.2f}%** vs cotação atual de R$ {current_price:.2f}). "
                f"1 Lote Padrão (100 ações) = **R$ {custom_price * 100:,.2f}**."
            )

    st.markdown("---")

    col_val_to_qty, col_qty_to_val = st.columns(2)

    # ==========================================================================
    # COLUNA 1: VALOR (R$) -> QUANTIDADE DE AÇÕES
    # ==========================================================================
    with col_val_to_qty:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(17, 24, 39, 0.85) 100%);
                        border: 1px solid #10b981; border-left: 5px solid #10b981; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px;">
                <span style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">💵 Tenho um Valor (R$) ➔ Quantas Ações terei?</span><br>
                <span style="font-size: 0.85rem; color: #9ca3af;">Simule quantas ações você compra com seu aporte financeiro</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        val_input_key = f"calc_val_input_{ticker}"
        pending_val_key = f"_pending_{val_input_key}"
        if pending_val_key in st.session_state:
            st.session_state[val_input_key] = float(st.session_state.pop(pending_val_key))
        elif val_input_key not in st.session_state:
            st.session_state[val_input_key] = 1000.0

        def _set_aporte_val(novo_valor: float, k_widget: str = val_input_key, k_pending: str = pending_val_key):
            st.session_state[k_pending] = float(novo_valor)
            try:
                st.session_state[k_widget] = float(novo_valor)
            except Exception:
                pass

        valor_aporte = st.number_input(
            "Valor disponível para investir (R$):",
            min_value=0.0,
            step=100.0,
            format="%.2f",
            key=val_input_key
        )

        # Botões rápidos de aporte (suporta tanto on_click quanto clique direto via chave pendente)
        st.caption("⚡ Atalhos de aporte:")
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("R$ 500", key=f"btn_v500_{ticker}", use_container_width=True, on_click=_set_aporte_val, args=(500.0,)):
                if valor_aporte != 500.0:
                    st.session_state[pending_val_key] = 500.0
                    st.rerun()
        with b2:
            if st.button("R$ 1.000", key=f"btn_v1k_{ticker}", use_container_width=True, on_click=_set_aporte_val, args=(1000.0,)):
                if valor_aporte != 1000.0:
                    st.session_state[pending_val_key] = 1000.0
                    st.rerun()
        with b3:
            if st.button("R$ 5.000", key=f"btn_v5k_{ticker}", use_container_width=True, on_click=_set_aporte_val, args=(5000.0,)):
                if valor_aporte != 5000.0:
                    st.session_state[pending_val_key] = 5000.0
                    st.rerun()
        with b4:
            if st.button("R$ 10.000", key=f"btn_v10k_{ticker}", use_container_width=True, on_click=_set_aporte_val, args=(10000.0,)):
                if valor_aporte != 10000.0:
                    st.session_state[pending_val_key] = 10000.0
                    st.rerun()

        qtd_total_acoes = int(valor_aporte // custom_price) if custom_price > 0 else 0
        custo_efetivo = qtd_total_acoes * custom_price
        troco = max(0.0, valor_aporte - custo_efetivo)

        lotes_padrao = qtd_total_acoes // 100
        qtd_lote_padrao = lotes_padrao * 100
        qtd_fracionario = qtd_total_acoes % 100

        m_a1, m_a2 = st.columns(2)
        with m_a1:
            st.metric(
                label="Total de Ações Inteiras",
                value=f"{qtd_total_acoes:,} ações".replace(",", "."),
                delta=f"Custo real: R$ {custo_efetivo:,.2f}"
            )
        with m_a2:
            st.metric(
                label="Troco Restante (Caixa)",
                value=f"R$ {troco:,.2f}",
                delta=f"Faltam R$ {max(0.0, custom_price - troco):,.2f} p/ +1 ação",
                delta_color="off"
            )

        # Detalhamento Lote Padrão vs Fracionário B3
        ordem_lote_str = f"<b>{qtd_lote_padrao:,} ações</b> ({lotes_padrao} lote(s) via <code>{clean_ticker}</code>)".replace(",", ".")
        ordem_frac_str = f"<b>{qtd_fracionario} ações</b> (mercado fracionário via <code>{clean_ticker}F</code>)"

        dy_html_left = ""
        if has_dy and qtd_total_acoes > 0:
            div_anual_est = custo_efetivo * dy_decimal
            div_mensal_est = div_anual_est / 12.0
            dy_html_left = (
                f"<div style='margin-top: 8px; padding-top: 8px; border-top: 1px solid #374151; color: #a7f3d0;'>"
                f"💰 <b>Dividendos Estimados (DY {dy_decimal*100:.2f}% a.a.):</b> "
                f"~<b>R$ {div_anual_est:,.2f}/ano</b> (~R$ {div_mensal_est:,.2f}/mês)"
                f"</div>"
            )

        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-radius: 8px; padding: 12px 16px; margin-top: 6px; font-size: 0.9rem; color: #e5e7eb;">
                📦 <b>Como enviar a ordem na B3:</b><br>
                • Lote Padrão: {ordem_lote_str} = <b>R$ {qtd_lote_padrao * custom_price:,.2f}</b><br>
                • Fracionário: {ordem_frac_str} = <b>R$ {qtd_fracionario * custom_price:,.2f}</b>
                {dy_html_left}
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==========================================================================
    # COLUNA 2: QUANTIDADE DE AÇÕES -> VALOR NECESSÁRIO (R$)
    # ==========================================================================
    with col_qty_to_val:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, rgba(56, 189, 248, 0.12) 0%, rgba(17, 24, 39, 0.85) 100%);
                        border: 1px solid #38bdf8; border-left: 5px solid #38bdf8; border-radius: 10px; padding: 14px 18px; margin-bottom: 14px;">
                <span style="font-size: 1.1rem; font-weight: 700; color: #ffffff;">📈 Quero X Ações ➔ Qual Valor (R$) preciso?</span><br>
                <span style="font-size: 0.85rem; color: #9ca3af;">Descubra o patrimônio total correspondente a uma quantidade de ações</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        qty_input_key = f"calc_qty_input_{ticker}"
        pending_qty_key = f"_pending_{qty_input_key}"
        if pending_qty_key in st.session_state:
            st.session_state[qty_input_key] = int(st.session_state.pop(pending_qty_key))
        elif qty_input_key not in st.session_state:
            st.session_state[qty_input_key] = 100

        def _set_qtd_val(nova_qtd: int, k_widget: str = qty_input_key, k_pending: str = pending_qty_key):
            st.session_state[k_pending] = int(nova_qtd)
            try:
                st.session_state[k_widget] = int(nova_qtd)
            except Exception:
                pass

        qtd_desejada = st.number_input(
            f"Quantidade desejada de ações ({clean_ticker}):",
            min_value=1,
            step=10,
            format="%d",
            key=qty_input_key
        )

        # Botões rápidos de quantidade (suporta tanto on_click quanto clique direto via chave pendente)
        st.caption("⚡ Atalhos de quantidade (Lotes):")
        q1, q2, q3, q4 = st.columns(4)
        with q1:
            if st.button("100 (1 Lote)", key=f"btn_q100_{ticker}", use_container_width=True, on_click=_set_qtd_val, args=(100,)):
                if qtd_desejada != 100:
                    st.session_state[pending_qty_key] = 100
                    st.rerun()
        with q2:
            if st.button("500 (5 Lotes)", key=f"btn_q500_{ticker}", use_container_width=True, on_click=_set_qtd_val, args=(500,)):
                if qtd_desejada != 500:
                    st.session_state[pending_qty_key] = 500
                    st.rerun()
        with q3:
            if st.button("1.000", key=f"btn_q1k_{ticker}", use_container_width=True, on_click=_set_qtd_val, args=(1000,)):
                if qtd_desejada != 1000:
                    st.session_state[pending_qty_key] = 1000
                    st.rerun()
        with q4:
            if st.button("5.000", key=f"btn_q5k_{ticker}", use_container_width=True, on_click=_set_qtd_val, args=(5000,)):
                if qtd_desejada != 5000:
                    st.session_state[pending_qty_key] = 5000
                    st.rerun()

        valor_total_necessario = qtd_desejada * custom_price
        lotes_q = qtd_desejada // 100
        frac_q = qtd_desejada % 100

        # Simulação comparativa na mínima e máxima do período
        min_period = float(metrics.get("min_period", custom_price))
        max_period = float(metrics.get("max_period", custom_price))
        val_na_min = qtd_desejada * min_period
        val_na_max = qtd_desejada * max_period

        m_b1, m_b2 = st.columns(2)
        with m_b1:
            st.metric(
                label="Valor Total Necessário",
                value=f"R$ {valor_total_necessario:,.2f}",
                delta=f"R$ {custom_price:,.2f} por ação",
                delta_color="off"
            )
        with m_b2:
            st.metric(
                label="Valor no Topo do Período",
                value=f"R$ {val_na_max:,.2f}",
                delta=f"{(val_na_max - valor_total_necessario):+,.2f} R$ vs atual"
            )

        dy_html_right = ""
        if has_dy and qtd_desejada > 0:
            div_anual_q = valor_total_necessario * dy_decimal
            div_mensal_q = div_anual_q / 12.0
            dy_html_right = (
                f"<div style='margin-top: 8px; padding-top: 8px; border-top: 1px solid #374151; color: #93c5fd;'>"
                f"💰 <b>Renda Passiva Estimada (DY {dy_decimal*100:.2f}% a.a.):</b> "
                f"~<b>R$ {div_anual_q:,.2f}/ano</b> (~R$ {div_mensal_q:,.2f}/mês)"
                f"</div>"
            )

        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-radius: 8px; padding: 12px 16px; margin-top: 6px; font-size: 0.9rem; color: #e5e7eb;">
                📊 <b>Composição & Faixa de Preço no Período:</b><br>
                • Equivalente a <b>{lotes_q} lote(s) padrão</b> ({lotes_q*100:,} ações) + <b>{frac_q} no fracionário</b><br>
                • Na Mínima do período (R$ {min_period:.2f}): <b>R$ {val_na_min:,.2f}</b> &nbsp;|&nbsp; Na Máxima (R$ {max_period:.2f}): <b>R$ {val_na_max:,.2f}</b>
                {dy_html_right}
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ==========================================================================
    # TABELAS DE REFERÊNCIA RÁPIDA (VALOR <-> AÇÕES)
    # ==========================================================================
    st.markdown("#### 📋 Tabelas de Referência Rápida")
    t_col1, t_col2 = st.columns(2)

    with t_col1:
        st.caption(f"💵 **Por Valor Investido** (a R$ {custom_price:.2f} por `{clean_ticker}`)")
        valores_ref = [500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
        linhas_val = []
        for v in valores_ref:
            q = int(v // custom_price)
            custo_r = q * custom_price
            troco_r = v - custo_r
            linhas_val.append({
                "Valor (R$)": f"R$ {v:,.2f}",
                "Qtd. Ações": f"{q:,}".replace(",", "."),
                "Lotes / Frac.": f"{q // 100}L + {q % 100}F",
                "Custo Real": f"R$ {custo_r:,.2f}",
                "Troco": f"R$ {troco_r:,.2f}"
            })
        st.dataframe(linhas_val, use_container_width=True, hide_index=True)

    with t_col2:
        st.caption(f"📈 **Por Quantidade de Ações** (a R$ {custom_price:.2f} por `{clean_ticker}`)")
        qtds_ref = [10, 50, 100, 200, 500, 1000, 2500, 5000]
        linhas_qtd = []
        for q in qtds_ref:
            custo_q = q * custom_price
            linha = {
                "Qtd. Ações": f"{q:,}".replace(",", "."),
                "Modalidade B3": f"{q // 100} Lote(s)" if q % 100 == 0 else f"Fracionário ({clean_ticker}F)",
                "Valor Total (R$)": f"R$ {custo_q:,.2f}",
                "Na Mínima": f"R$ {q * min_period:,.2f}",
                "Na Máxima": f"R$ {q * max_period:,.2f}"
            }
            linhas_qtd.append(linha)
        st.dataframe(linhas_qtd, use_container_width=True, hide_index=True)


import math
import plotly.graph_objects as go


def render_earnings_and_dividends_tab(ticker: str, company_name: str, metrics: dict, ticker_info: dict = None):
    """
    Renderiza a aba de Ganhos por Ação, Dividendos, Payout, Preço-Teto (Bazin / Graham)
    e Múltiplos Fundamentalistas do ativo.
    """
    current_price = float(metrics.get("current_price", 0.0))
    if current_price <= 0:
        st.warning("Cotação atual indisponível para calcular indicadores por ação.")
        return

    info = ticker_info if isinstance(ticker_info, dict) else {}
    clean_ticker = ticker.replace(".SA", "")

    def _safe_float(val):
        try:
            if val is None:
                return None
            f = float(val)
            return None if math.isnan(f) or math.isinf(f) else f
        except Exception:
            return None

    # 1. Lucro por Ação (LPA / EPS) e Valor Patrimonial por Ação (VPA / Book Value)
    lpa_ttm = _safe_float(info.get("trailingEps"))
    lpa_fwd = _safe_float(info.get("forwardEps"))
    annual_eps_hist = info.get("_annual_eps_history", {}) or {}
    if lpa_ttm is None and annual_eps_hist:
        latest_yr = sorted(annual_eps_hist.keys(), reverse=True)[0]
        lpa_ttm = _safe_float(annual_eps_hist.get(latest_yr))

    vpa = _safe_float(info.get("bookValue"))

    # 2. Dividendos por Ação (DPA 12m) e Dividend Yield (DY)
    dpa_12m = _safe_float(info.get("_calc_dpa_12m"))
    if dpa_12m is None or dpa_12m <= 0:
        dpa_12m = _safe_float(info.get("trailingAnnualDividendRate")) or _safe_float(info.get("dividendRate")) or 0.0

    div_count_12m = int(info.get("_calc_div_count_12m", 0) or 0)

    if dpa_12m > 0 and current_price > 0:
        dy_pct = (dpa_12m / current_price) * 100.0
    else:
        raw_dy = _safe_float(info.get("trailingAnnualDividendYield")) or _safe_float(info.get("dividendYield"))
        if raw_dy is not None and raw_dy > 0:
            dy_pct = raw_dy if raw_dy > 1.0 else raw_dy * 100.0
            if dpa_12m <= 0:
                dpa_12m = current_price * (dy_pct / 100.0)
        else:
            dy_pct = 0.0

    # 3. Payout Ratio (% do Lucro distribuído em proventos)
    raw_payout = _safe_float(info.get("payoutRatio"))
    if dpa_12m > 0 and lpa_ttm is not None and lpa_ttm > 0:
        payout_pct = (dpa_12m / lpa_ttm) * 100.0
    elif raw_payout is not None and raw_payout >= 0:
        payout_pct = raw_payout * 100.0 if raw_payout <= 5.0 else raw_payout
    else:
        payout_pct = None

    # 4. Múltiplos de Valuation e Rentabilidade (P/L, Earnings Yield, P/VP, ROE, Margem Líquida)
    pl_ratio = (current_price / lpa_ttm) if (lpa_ttm is not None and lpa_ttm != 0) else _safe_float(info.get("trailingPE"))
    earnings_yield_pct = ((lpa_ttm / current_price) * 100.0) if (lpa_ttm is not None and current_price > 0) else None
    pvp_ratio = (current_price / vpa) if (vpa is not None and vpa > 0) else _safe_float(info.get("priceToBook"))

    raw_roe = _safe_float(info.get("returnOnEquity"))
    roe_pct = (raw_roe * 100.0) if raw_roe is not None else None

    raw_margin = _safe_float(info.get("profitMargins"))
    margin_pct = (raw_margin * 100.0) if raw_margin is not None else None

    st.subheader(f"💰 Ganhos por Ação, Dividendos & Valuation: {clean_ticker} ({company_name})")
    st.markdown(
        f"Análise detalhada da **geração de lucro por ação (LPA)**, **remuneração ao acionista (DPA, Dividend Yield e Payout)** "
        f"e **preço justo / teto** para `{clean_ticker}` na cotação atual de **R$ {current_price:,.2f}**."
    )

    # ==========================================================================
    # 1. CARDS DE DESTAQUE (MÉTRICAS POR AÇÃO)
    # ==========================================================================
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        lpa_str = f"R$ {lpa_ttm:,.2f}" if lpa_ttm is not None else "N/D"
        ey_str = f"Earnings Yield: {earnings_yield_pct:+.2f}%" if earnings_yield_pct is not None else "Lucro líquido / ação (12m)"
        st.metric(
            label="Lucro por Ação (LPA 12m)",
            value=lpa_str,
            delta=ey_str,
            delta_color="normal" if (lpa_ttm or 0) >= 0 else "inverse",
            help="Quanto de lucro líquido a empresa gerou para cada 1 ação nos últimos 12 meses (EPS). O Earnings Yield (LPA/Preço) mostra a rentabilidade total gerada pela empresa sobre o preço da ação."
        )

    with k2:
        dpa_str = f"R$ {dpa_12m:,.2f}" if dpa_12m > 0 else "R$ 0,00"
        pag_str = f"{div_count_12m} pagamento(s) em 12m" if div_count_12m > 0 else "Proventos últimos 12m"
        st.metric(
            label="Dividendos por Ação (DPA 12m)",
            value=dpa_str,
            delta=pag_str,
            delta_color="off",
            help="Soma dos dividendos e JCP pagos por cada 1 ação nos últimos 12 meses."
        )

    with k3:
        dy_str = f"{dy_pct:.2f}%"
        dy_tag = "Acima de 6% a.a. (Bazin)" if dy_pct >= 6.0 else ("Moderado" if dy_pct >= 3.0 else "Baixo / Crescimento")
        st.metric(
            label="Dividend Yield (DY 12m)",
            value=dy_str,
            delta=dy_tag,
            delta_color="normal" if dy_pct >= 6.0 else "off",
            help="Retorno percentual em proventos nos últimos 12 meses em relação à cotação atual (DPA 12m ÷ Preço Atual)."
        )

    with k4:
        if payout_pct is not None:
            payout_str = f"{payout_pct:.1f}%"
            if payout_pct > 100:
                p_tag = "Acima do lucro (>100%)"
            elif payout_pct >= 50:
                p_tag = "Forte distribuição (Vacas Leiteiras)"
            elif payout_pct >= 25:
                p_tag = "Equilíbrio (Retenção + Dividendo)"
            else:
                p_tag = "Foco em Reinvestimento"
        elif lpa_ttm is not None and lpa_ttm < 0:
            payout_str = "LPA Negativo"
            p_tag = "Prejuízo contábil 12m"
        else:
            payout_str = "N/D"
            p_tag = "Sem dados de distribuição"

        st.metric(
            label="Payout (DPA ÷ LPA)",
            value=payout_str,
            delta=p_tag,
            delta_color="off",
            help="Percentual do lucro líquido por ação (LPA) que é distribuído aos acionistas na forma de dividendos/JCP (DPA). O restante é retido pela empresa para reinvestimento ou redução de dívida."
        )

    # Segunda linha de métricas fundamentalistas por ação
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        pl_str = f"{pl_ratio:.2f}x" if pl_ratio is not None else "N/D"
        pl_sub = f"LPA Proj.: R$ {lpa_fwd:.2f}" if lpa_fwd is not None else "Anos p/ retorno via lucro"
        st.metric(
            label="P/L (Preço ÷ Lucro)",
            value=pl_str,
            delta=pl_sub,
            delta_color="off",
            help="Indica quantas vezes o preço atual equivale ao lucro anual por ação (ou quantos anos levaria para reaver o capital via lucro líquido constante)."
        )

    with m2:
        vpa_str = f"R$ {vpa:,.2f}" if vpa is not None else "N/D"
        pvp_str = f"P/VP: {pvp_ratio:.2f}x" if pvp_ratio is not None else "Patrimônio Líq. / Ação"
        st.metric(
            label="VPA (Valor Patrimonial / Ação)",
            value=vpa_str,
            delta=pvp_str,
            delta_color="off",
            help="Patrimônio líquido contábil da empresa dividido pelo total de ações. P/VP < 1,0x indica que a ação negocia abaixo do patrimônio contábil."
        )

    with m3:
        roe_str = f"{roe_pct:.1f}%" if roe_pct is not None else "N/D"
        marg_str = f"Margem Líq.: {margin_pct:.1f}%" if margin_pct is not None else "Retorno s/ Patrimônio"
        st.metric(
            label="ROE (Retorno s/ Patrimônio)",
            value=roe_str,
            delta=marg_str,
            delta_color="normal" if (roe_pct or 0) >= 15.0 else "off",
            help="Mede a rentabilidade que a empresa gera sobre o patrimônio líquido dos acionistas (Lucro Líquido ÷ Patrimônio Líquido)."
        )

    with m4:
        if lpa_ttm is not None and lpa_ttm > 0:
            lucro_retido = max(0.0, lpa_ttm - dpa_12m)
            ret_pct = (lucro_retido / lpa_ttm) * 100.0
            ret_str = f"R$ {lucro_retido:,.2f}"
            ret_sub = f"{ret_pct:.1f}% retido na empresa"
        else:
            ret_str = "N/D"
            ret_sub = "LPA - DPA"
        st.metric(
            label="Lucro Retido por Ação",
            value=ret_str,
            delta=ret_sub,
            delta_color="off",
            help="Parcela do lucro por ação (LPA - DPA) que permanece no caixa da companhia para financiar crescimento, aquisições ou amortizar dívidas."
        )

    # ==========================================================================
    # 2. BARRA VISUAL DE DESTINAÇÃO DO LUCRO POR AÇÃO (PAYOUT vs RETENÇÃO)
    # ==========================================================================
    if lpa_ttm is not None and lpa_ttm > 0:
        pct_dist = min(100.0, max(0.0, (dpa_12m / lpa_ttm) * 100.0))
        pct_ret = max(0.0, 100.0 - pct_dist)
        excesso_txt = (
            f" ⚠️ <i>Nota: O DPA (R$ {dpa_12m:.2f}) superou o LPA contábil (R$ {lpa_ttm:.2f}) em {((dpa_12m/lpa_ttm)-1)*100:.1f}%, indicando uso de reservas de lucros ou geração de caixa acumulada.</i>"
            if dpa_12m > lpa_ttm else ""
        )
        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-radius: 10px; padding: 14px 18px; margin: 10px 0 16px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap;">
                    <span style="font-size: 0.95rem; font-weight: 700; color: #f3f4f6;">
                        🍰 Destinação de Cada R$ {lpa_ttm:.2f} de Lucro por Ação (LPA):
                    </span>
                    <span style="font-size: 0.85rem; color: #9ca3af;">
                        <b style="color: #10b981;">🟢 Distribuído (Payout): {pct_dist:.1f}% (R$ {dpa_12m:.2f})</b> &nbsp;|&nbsp;
                        <b style="color: #38bdf8;">🔵 Retido p/ Reinvestimento: {pct_ret:.1f}% (R$ {max(0.0, lpa_ttm - dpa_12m):.2f})</b>
                    </span>
                </div>
                <div style="width: 100%; height: 14px; background-color: #1e293b; border-radius: 999px; overflow: hidden; display: flex;">
                    <div style="width: {pct_dist:.1f}%; background: linear-gradient(90deg, #10b981, #059669); height: 100%;"></div>
                    <div style="width: {pct_ret:.1f}%; background: linear-gradient(90deg, #0284c7, #38bdf8); height: 100%;"></div>
                </div>
                <div style="font-size: 0.82rem; color: #9ca3af; margin-top: 6px;">
                    A empresa converte cada ação em <b>R$ {lpa_ttm:.2f}</b> de lucro anual, pagando <b>R$ {dpa_12m:.2f}</b> diretamente ao bolso do acionista.{excesso_txt}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ==========================================================================
    # 3. PREÇO-TETO BAZIN (DIVIDENDOS) & PREÇO JUSTO DE GRAHAM (LPA x VPA)
    # ==========================================================================
    st.markdown("#### 🎯 Termômetro de Valuation por Ação: Preço-Teto (Bazin) & Valor Intrínseco (Graham)")
    col_bazin, col_graham = st.columns(2)

    with col_bazin:
        meta_dy_bazin = st.slider(
            "Meta de Dividend Yield Mínimo Exigido — Método Décio Bazin (% a.a.):",
            min_value=4.0,
            max_value=14.0,
            value=6.0,
            step=0.5,
            key=f"slider_bazin_{ticker}",
            help="Décio Bazin preconizava comprar ações que pagam pelo menos 6% ao ano em dividendos. Preço-Teto = DPA ÷ Meta de DY."
        )
        if dpa_12m > 0:
            preco_teto_bazin = dpa_12m / (meta_dy_bazin / 100.0)
            margem_bazin_pct = ((preco_teto_bazin - current_price) / current_price) * 100.0
            bazin_cor = "#10b981" if preco_teto_bazin >= current_price else "#f59e0b"
            bazin_status = "✅ Abaixo do Preço-Teto (Margem Positiva)" if preco_teto_bazin >= current_price else "⚠️ Acima do Preço-Teto para o DY exigido"
            st.markdown(
                f"""
                <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 5px solid {bazin_cor}; border-radius: 10px; padding: 14px 18px;">
                    <div style="font-size: 0.9rem; color: #9ca3af; font-weight: 600;">📌 Preço-Teto de Bazin (DY Alvo de {meta_dy_bazin:.1f}% a.a.)</div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin: 6px 0;">
                        <span style="font-size: 1.5rem; font-weight: 800; color: #ffffff;">R$ {preco_teto_bazin:,.2f}</span>
                        <span style="font-size: 0.95rem; font-weight: 700; color: {bazin_cor};">{margem_bazin_pct:+.1f}% vs Cotação Atual</span>
                    </div>
                    <div style="font-size: 0.84rem; color: #d1d5db;">
                        {bazin_status}<br>
                        <span style="color: #9ca3af;">Fórmula: DPA 12m (R$ {dpa_12m:.2f}) ÷ {meta_dy_bazin:.1f}% = R$ {preco_teto_bazin:,.2f}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("ℹ️ Ativo sem distribuição de dividendos nos últimos 12 meses para cálculo do Preço-Teto de Bazin.")

    with col_graham:
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        if lpa_ttm is not None and lpa_ttm > 0 and vpa is not None and vpa > 0:
            valor_graham = math.sqrt(22.5 * lpa_ttm * vpa)
            margem_graham_pct = ((valor_graham - current_price) / current_price) * 100.0
            graham_cor = "#10b981" if valor_graham >= current_price else "#f59e0b"
            graham_status = "✅ Descontada pela Fórmula de Graham" if valor_graham >= current_price else "⚠️ Negociando com prêmio sobre Graham"
            st.markdown(
                f"""
                <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 5px solid {graham_cor}; border-radius: 10px; padding: 14px 18px; margin-top: 16px;">
                    <div style="font-size: 0.9rem; color: #9ca3af; font-weight: 600;">📐 Valor Intrínseco de Benjamin Graham (√[22,5 × LPA × VPA])</div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin: 6px 0;">
                        <span style="font-size: 1.5rem; font-weight: 800; color: #ffffff;">R$ {valor_graham:,.2f}</span>
                        <span style="font-size: 0.95rem; font-weight: 700; color: {graham_cor};">{margem_graham_pct:+.1f}% vs Cotação Atual</span>
                    </div>
                    <div style="font-size: 0.84rem; color: #d1d5db;">
                        {graham_status}<br>
                        <span style="color: #9ca3af;">Fórmula: √(22,5 × R$ {lpa_ttm:.2f} × R$ {vpa:.2f}) — limite clássico P/L ≤ 15x e P/VP ≤ 1,5x.</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info(
                "ℹ️ **Fórmula de Benjamin Graham (√[22,5 × LPA × VPA]):** "
                "Requer LPA e VPA positivos. Quando um deles é negativo ou indisponível, o cálculo não se aplica."
            )

    st.markdown("---")

    # ==========================================================================
    # 4. HISTÓRICO DE DIVIDENDOS E LUCRO POR AÇÃO (GRÁFICO + TABELA DE PAGAMENTOS)
    # ==========================================================================
    yearly_divs = info.get("_yearly_dividends", {}) or {}
    recent_divs = info.get("_recent_dividends", []) or []

    col_hist_chart, col_hist_table = st.columns([1.4, 1.0])

    with col_hist_chart:
        st.markdown("#### 📊 Evolução Anual: Lucro por Ação (LPA) vs Dividendos Pagos (DPA)")
        all_years = sorted(set(list(yearly_divs.keys()) + list(annual_eps_hist.keys())))
        if all_years:
            dpa_vals = [round(float(yearly_divs.get(y, 0.0)), 4) for y in all_years]
            lpa_vals = [round(float(annual_eps_hist[y]), 4) if y in annual_eps_hist else None for y in all_years]

            fig_earn = go.Figure()
            if any(v is not None for v in lpa_vals):
                fig_earn.add_trace(
                    go.Bar(
                        x=all_years,
                        y=lpa_vals,
                        name="Lucro por Ação (LPA)",
                        marker_color="#38bdf8",
                        text=[f"R$ {v:.2f}" if v is not None else "" for v in lpa_vals],
                        textposition="auto"
                    )
                )
            if any(v > 0 for v in dpa_vals):
                fig_earn.add_trace(
                    go.Bar(
                        x=all_years,
                        y=dpa_vals,
                        name="Dividendos por Ação (DPA)",
                        marker_color="#10b981",
                        text=[f"R$ {v:.2f}" if v > 0 else "" for v in dpa_vals],
                        textposition="auto"
                    )
                )

            fig_earn.update_layout(
                template="plotly_dark",
                barmode="group",
                plot_bgcolor="#111827",
                paper_bgcolor="#0e1117",
                yaxis=dict(title="R$ por Ação", tickprefix="R$ ", gridcolor="#1f2937"),
                xaxis=dict(title="Ano", type="category", gridcolor="#1f2937"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=40, b=20),
                height=340
            )
            st.plotly_chart(fig_earn, use_container_width=True)
        else:
            st.info("Histórico anual de LPA e Dividendos indisponível no Yahoo Finance para este ativo.")

    with col_hist_table:
        st.markdown("#### 🗓️ Últimos Proventos Pagos por Ação")
        if recent_divs:
            rows_div = []
            for ev in recent_divs:
                val_ev = float(ev["valor"])
                dy_unit = (val_ev / current_price) * 100.0 if current_price > 0 else 0.0
                rows_div.append({
                    "Data Ex": ev["data"],
                    "Valor / Ação": f"R$ {val_ev:.4f}",
                    "Por 100 Ações (1 Lote)": f"R$ {val_ev * 100:,.2f}",
                    "Yield s/ Cotação": f"{dy_unit:.2f}%"
                })
            st.dataframe(rows_div, use_container_width=True, hide_index=True, height=340)
        else:
            st.info("Nenhum pagamento recente de dividendo/JCP registrado para este ticker.")

    st.markdown("---")

    # ==========================================================================
    # 5. DIAGNÓSTICO AUTOMÁTICO DAS SITUAÇÕES ATUAIS DO ATIVO
    # ==========================================================================
    st.markdown(f"#### 🧭 Diagnóstico Explicado: O que os números de `{clean_ticker}` significam hoje?")

    # Interpretação dinâmica de cada situação
    if lpa_ttm is None:
        sit_lpa_badge = "⚪ LPA Indisponível"
        sit_lpa_cor = "#6b7280"
        sit_lpa_desc = "O Yahoo Finance não reportou o Lucro por Ação (EPS) acumulado dos últimos 12 meses para este ticker."
    elif lpa_ttm > 0:
        ey_txt = f" ({earnings_yield_pct:.1f}% de Earnings Yield sobre a cotação atual)" if earnings_yield_pct is not None else ""
        sit_lpa_badge = "🟢 Empresa Lucrativa"
        sit_lpa_cor = "#10b981"
        sit_lpa_desc = (
            f"Cada ação gerou <b>R$ {lpa_ttm:.2f}</b> de lucro líquido nos últimos 12 meses{ey_txt}. "
            "Significa que a operação é superavitária e gera valor real que pode ser distribuído em dividendos ou reinvestido."
        )
    else:
        sit_lpa_badge = "🔴 Prejuízo Contábil (LPA Negativo)"
        sit_lpa_cor = "#ef4444"
        sit_lpa_desc = (
            f"A empresa registrou prejuízo de <b>R$ {lpa_ttm:.2f} por ação</b> nos últimos 12 meses. "
            "Nessa situação, o múltiplo P/L fica negativo/distorcido e eventuais dividendos pagos saem de reservas de caixa anteriores."
        )

    if dy_pct >= 6.0:
        sit_dy_badge = "🟢 Pagadora Forte de Dividendos (≥ 6% a.a.)"
        sit_dy_cor = "#10b981"
        sit_dy_desc = (
            f"Com Dividend Yield de <b>{dy_pct:.2f}%</b> (R$ {dpa_12m:.2f}/ação), o ativo supera o piso clássico de <b>6% ao ano</b> "
            "de Décio Bazin e Luiz Barsi, sendo característico de empresas geradoras de renda passiva."
        )
    elif dy_pct >= 3.0:
        sit_dy_badge = "🟡 Dividendos Moderados (3% a 6% a.a.)"
        sit_dy_cor = "#f59e0b"
        sit_dy_desc = (
            f"O retorno em proventos é de <b>{dy_pct:.2f}%</b> (R$ {dpa_12m:.2f}/ação). "
            "Remunera o acionista de forma equilibrada, geralmente combinando distribuição parcial com retenção para crescimento."
        )
    elif dy_pct > 0:
        sit_dy_badge = "🔵 Dividendos Baixos / Foco em Crescimento (< 3% a.a.)"
        sit_dy_cor = "#38bdf8"
        sit_dy_desc = (
            f"O Dividend Yield atual é de <b>{dy_pct:.2f}%</b> (R$ {dpa_12m:.2f}/ação). "
            "Típico de empresas que priorizam reinvestir o caixa no próprio negócio (ou cujo preço da ação subiu rápido frente ao dividendo)."
        )
    else:
        sit_dy_badge = "⚪ Sem Proventos nos Últimos 12 Meses"
        sit_dy_cor = "#6b7280"
        sit_dy_desc = "O ativo não distribuiu dividendos ou JCP nos últimos 12 meses (foco 100% em retenção/crescimento ou reestruturação financeira)."

    if payout_pct is None:
        sit_pay_badge = "⚪ Payout Não Calculável"
        sit_pay_cor = "#6b7280"
        sit_pay_desc = "Como o lucro por ação é negativo ou não há distribuição reportada, a razão DPA ÷ LPA não se aplica."
    elif payout_pct > 100.0:
        sit_pay_badge = "🟠 Payout Acima do Lucro (> 100%)"
        sit_pay_cor = "#f59e0b"
        sit_pay_desc = (
            f"A empresa distribuiu <b>{payout_pct:.1f}%</b> do lucro líquido contábil. "
            "Isso ocorre quando a companhia usa <b>reservas de lucros acumulados</b> de anos anteriores ou tem geração de caixa livre (FCO) superior ao lucro contábil. Exige acompanhar se é pontual ou recorrente."
        )
    elif payout_pct >= 50.0:
        sit_pay_badge = "🟢 Perfil 'Vaca Leiteira' (Payout 50% a 100%)"
        sit_pay_cor = "#10b981"
        sit_pay_desc = (
            f"Distribui a maior parte do lucro (<b>{payout_pct:.1f}%</b>) aos acionistas. "
            "Perfil típico de empresas maduras (elétricas, bancos, saneamento, seguradoras) que já têm fluxo de caixa consolidado e pouca necessidade de grandes investimentos em expansão."
        )
    elif payout_pct >= 25.0:
        sit_pay_badge = "🔵 Perfil Equilibrado (Payout 25% a 50%)"
        sit_pay_cor = "#38bdf8"
        sit_pay_desc = (
            f"Distribui <b>{payout_pct:.1f}%</b> do lucro (acima do dividendo mínimo obrigatório de 25% da Lei das S.A.) "
            f"e retém <b>{100.0 - payout_pct:.1f}%</b> para financiar novos projetos, modernização ou abatimento de dívida."
        )
    else:
        sit_pay_badge = "🟣 Perfil Retenção / Crescimento (Payout < 25%)"
        sit_pay_cor = "#a855f7"
        sit_pay_desc = (
            f"Distribui apenas <b>{payout_pct:.1f}%</b> do lucro e retém a quase totalidade no caixa. "
            "O objetivo aqui é que o ganho do investidor venha da <b>valorização da cotação (ganho de capital)</b> impulsionada pelo crescimento futuro dos lucros."
        )

    if pl_ratio is not None and pl_ratio > 0:
        if pl_ratio <= 8.0:
            pl_comment = f"<b>P/L de {pl_ratio:.1f}x</b> (descontado/barato frente à média histórica da B3, ou mercado precificando queda nos lucros futuros)"
        elif pl_ratio <= 15.0:
            pl_comment = f"<b>P/L de {pl_ratio:.1f}x</b> (faixa intermediária/justa segundo o limite clássico de 15x de Benjamin Graham)"
        else:
            pl_comment = f"<b>P/L de {pl_ratio:.1f}x</b> (múltiplo esticado: o mercado paga caro hoje esperando forte crescimento dos lucros nos próximos anos)"
    else:
        pl_comment = "<b>P/L não aplicável</b> (lucro negativo ou indisponível)"

    if pvp_ratio is not None and pvp_ratio > 0:
        if pvp_ratio < 1.0:
            pvp_comment = f"<b>P/VP de {pvp_ratio:.2f}x</b> (ação negociada <b>abaixo</b> do valor contábil do seu patrimônio líquido)"
        elif pvp_ratio <= 2.0:
            pvp_comment = f"<b>P/VP de {pvp_ratio:.2f}x</b> (negociada próxima ou com prêmio moderado sobre o patrimônio líquido)"
        else:
            pvp_comment = f"<b>P/VP de {pvp_ratio:.2f}x</b> (prêmio elevado sobre o patrimônio; comum em empresas leves em ativos físicos e com **ROE alto**)"
    else:
        pvp_comment = "<b>P/VP indisponível</b>"

    sit_val_badge = "📐 Múltiplos P/L & P/VP"
    sit_val_cor = "#60a5fa"
    sit_val_desc = f"Na cotação de R$ {current_price:.2f}, o ativo apresenta {pl_comment} e {pvp_comment}."

    diag_c1, diag_c2 = st.columns(2)
    with diag_c1:
        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 4px solid {sit_lpa_cor}; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: {sit_lpa_cor}; font-size: 0.95rem; margin-bottom: 4px;">{sit_lpa_badge}</div>
                <div style="font-size: 0.86rem; color: #d1d5db; line-height: 1.45;">{sit_lpa_desc}</div>
            </div>
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 4px solid {sit_pay_cor}; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: {sit_pay_cor}; font-size: 0.95rem; margin-bottom: 4px;">{sit_pay_badge}</div>
                <div style="font-size: 0.86rem; color: #d1d5db; line-height: 1.45;">{sit_pay_desc}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with diag_c2:
        st.markdown(
            f"""
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 4px solid {sit_dy_cor}; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: {sit_dy_cor}; font-size: 0.95rem; margin-bottom: 4px;">{sit_dy_badge}</div>
                <div style="font-size: 0.86rem; color: #d1d5db; line-height: 1.45;">{sit_dy_desc}</div>
            </div>
            <div style="background-color: rgba(255, 255, 255, 0.03); border: 1px solid #2d3748; border-left: 4px solid {sit_val_cor}; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px;">
                <div style="font-weight: 700; color: {sit_val_cor}; font-size: 0.95rem; margin-bottom: 4px;">{sit_val_badge}</div>
                <div style="font-size: 0.86rem; color: #d1d5db; line-height: 1.45;">{sit_val_desc}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ==========================================================================
    # 6. GUIA DE LEITURA E GLOSSÁRIO COMPLETO DOS PARÂMETROS E SITUAÇÕES
    # ==========================================================================
    with st.expander("📖 Legenda Completa & Guia de Interpretação (O que significa cada parâmetro e situação)", expanded=True):
        g_col1, g_col2 = st.columns(2)

        with g_col1:
            st.markdown("##### 💰 1. Indicadores de Ganhos e Proventos por Ação")
            st.markdown(
                "- **LPA (Lucro por Ação / EPS):** É o `Lucro Líquido Total ÷ Número Total de Ações`. Representa a fatia de lucro que pertence a cada 1 ação.\n"
                "  - 🟢 **LPA Positivo e Crescente:** A empresa dá lucro e está expandindo resultados.\n"
                "  - 🔴 **LPA Negativo:** A empresa operou no prejuízo nos últimos 12 meses.\n"
                "- **Earnings Yield (`LPA ÷ Preço`):** É o inverso do P/L expresso em porcentagem. Mostra quanto a empresa gera de lucro anual em relação ao preço que você paga pela ação hoje (ex.: LPA de R$ 4,00 numa ação de R$ 40,00 = **10% ao ano** de geração de lucro).\n"
                "- **DPA (Dividendo por Ação):** Soma em reais (`R$`) de todos os **Dividendos e JCP** efetivamente pagos para cada 1 ação nos últimos 12 meses.\n"
                "- **Dividend Yield — DY (`DPA ÷ Preço Atual`):** Percentual de retorno anual apenas em proventos sobre a cotação atual.\n"
                "  - 🟢 **Acima de 6% a.a.:** Considerado excelente para estratégias de renda passiva (critério Décio Bazin).\n"
                "  - 🟡 **Entre 3% e 6% a.a.:** Retorno moderado; comum em empresas que dividem o lucro entre dividendos e expansão.\n"
                "  - 🔵 **Abaixo de 3% a.a.:** Baixa distribuição; comum em empresas de crescimento (*growth*) ou quando a ação subiu muito rápido.\n"
                "- **Data Ex (Ex-Dividendo):** Data de corte na B3. Quem dorme com a ação na véspera (*Data Com*) tem direito a receber o provento; a partir da *Data Ex*, quem compra a ação não recebe aquele pagamento específico."
            )

            st.markdown("##### 🍰 2. Faixas de Payout (`DPA ÷ LPA`) e Retenção")
            st.markdown(
                "- **Payout:** Mostra qual porcentagem do lucro líquido virou dividendo no bolso do acionista.\n"
                "  - 🟣 **0% a 25% (Foco em Crescimento):** A empresa retém quase todo o lucro para abrir novas fábricas, lojas, tecnologia ou pagar dívidas.\n"
                "  - 🔵 **25% a 50% (Equilíbrio):** Cumpre o dividendo mínimo obrigatório (normalmente 25% no Brasil) e reinveste a maior parte para continuar crescendo.\n"
                "  - 🟢 **50% a 95% (Vaca Leiteira / Maturidade):** Empresa madura e grande geradora de caixa que não precisa reter muito capital e distribui a maior parte aos sócios.\n"
                "  - 🟠 **Acima de 100% (Atenção):** A empresa pagou mais dividendos do que lucrou no ano. Pode ser positivo se vier de **reservas de lucros acumuladas** ou excesso de caixa, mas é um alerta se a empresa estiver se endividando para pagar dividendos.\n"
                "- **Lucro Retido por Ação (`LPA - DPA`):** Dinheiro que ficou dentro da empresa por cada ação para gerar mais lucro nos próximos anos."
            )

        with g_col2:
            st.markdown("##### 📐 3. Múltiplos de Valuation e Eficiência")
            st.markdown(
                "- **P/L (`Preço ÷ LPA`):** Quantos anos de lucro atual seriam necessários para 'pagar' o preço da ação.\n"
                "  - 🟢 **P/L Baixo (ex.: 4x a 8x):** Ação potencialmente barata/descontada (ou mercado cético com o setor).\n"
                "  - 🟡 **P/L Moderado (ex.: 9x a 15x):** Preço justo para empresas sólidas e estáveis.\n"
                "  - 🟠 **P/L Alto (> 15x ou 20x):** O mercado está pagando um prêmio alto hoje porque espera que o lucro cresça muito no futuro.\n"
                "- **VPA (Valor Patrimonial por Ação):** É o `Patrimônio Líquido Contábil ÷ Total de Ações` (tudo o que a empresa possui de bens/caixa menos todas as dívidas, dividido por ação).\n"
                "- **P/VP (`Preço ÷ VPA`):** Compara a cotação na bolsa com o patrimônio contábil da empresa.\n"
                "  - 🟢 **P/VP < 1,0x:** A ação custa na bolsa **menos** do que vale o patrimônio líquido contábil dela (desconto patrimonial).\n"
                "  - 🔵 **P/VP entre 1,0x e 2,0x:** Faixa normal para empresas rentáveis.\n"
                "  - 🟣 **P/VP > 2,0x:** Normal em empresas de tecnologia, marcas fortes ou alto ROE (que geram muito lucro precisando de pouco patrimônio físico).\n"
                "- **ROE (`Lucro Líquido ÷ Patrimônio Líquido`):** Mede a eficiência da gestão. Um **ROE ≥ 15%** indica uma empresa altamente rentável que multiplica bem o dinheiro próprio."
            )

            st.markdown("##### 🎯 4. Referências de Preço-Teto e Preço Justo")
            st.markdown(
                "- **Preço-Teto de Décio Bazin (`DPA 12m ÷ Meta de DY`):**\n"
                "  - Calcula o **preço máximo** que você pode pagar pela ação para garantir o Dividend Yield desejado (padrão de **6% a.a.**).\n"
                "  - ✅ **Cotação Abaixo do Preço-Teto:** Significa que, mantendo os dividendos atuais, quem compra hoje recebe **mais** do que a meta escolhida no slider.\n"
                "  - ⚠️ **Cotação Acima do Preço-Teto:** O dividendo atual remunera **menos** que a meta escolhida na cotação de hoje.\n"
                "- **Valor Intrínseco de Benjamin Graham (`√[22,5 × LPA × VPA]`):**\n"
                "  - Criado pelo mentor de Warren Buffett para encontrar o preço justo combinando **capacidade de lucro (LPA)** e **solidez patrimonial (VPA)** (baseado no teto de `P/L = 15` × `P/VP = 1,5` = `22,5`).\n"
                "  - ✅ **Margem Positiva vs Cotação:** Ação negociada com desconto de segurança em relação aos seus fundamentos contábeis.\n"
                "  - ⚠️ **Margem Negativa vs Cotação:** Ação negociada acima do limite conservador de Graham (comum em empresas de alto crescimento)."
            )


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

