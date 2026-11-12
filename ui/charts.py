"""
Módulo de renderização de gráficos interativos (Plotly).
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(hist: pd.DataFrame, symbol: str, current_price: float = None) -> go.Figure:
    """
    Cria um gráfico Candlestick profissional com médias móveis de 9 e 21 períodos
    e painel inferior sincronizado de Volume via Plotly.
    Oculta finais de semana para eliminar lacunas vazias no gráfico de ações da B3.
    Destaca a cotação de hoje / preço atual com linha d'água de referência.
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.75, 0.25],
        subplot_titles=(
            f"<b>{symbol}</b> — Histórico Candlestick com MMA 9 & MMA 21",
            "Volume Financeiro de Negociação"
        )
    )

    # 1. Candlestick principal
    fig.add_trace(
        go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name="Cotação (OHLC)",
            increasing_line_color="#10b981",  # Verde
            increasing_fillcolor="#10b981",
            decreasing_line_color="#ef4444",  # Vermelho
            decreasing_fillcolor="#ef4444"
        ),
        row=1, col=1
    )

    # 2. Média Móvel de 9 períodos (MMA 9)
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist['SMA9'],
            mode='lines',
            name="MMA 9 períodos",
            line=dict(color="#38bdf8", width=1.8),
            hoverinfo="y+name"
        ),
        row=1, col=1
    )

    # 3. Média Móvel de 21 períodos (MMA 21)
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist['SMA21'],
            mode='lines',
            name="MMA 21 períodos",
            line=dict(color="#f59e0b", width=1.8),
            hoverinfo="y+name"
        ),
        row=1, col=1
    )

    # 4. Linha horizontal destacando a cotação de hoje / preço atual
    target_price = current_price if (current_price and current_price > 0) else hist['Close'].iloc[-1]
    last_date = hist.index[-1]
    
    # Formata data legível do último candle
    try:
        last_date_str = last_date.strftime("%d/%m")
    except Exception:
        last_date_str = "Hoje"

    fig.add_hline(
        y=target_price,
        line_dash="dash",
        line_color="#60a5fa",
        line_width=1.5,
        annotation_text=f" Hoje ({last_date_str}): R$ {target_price:.2f} ",
        annotation_position="top left",
        annotation_font=dict(size=12, color="#ffffff"),
        annotation_bgcolor="rgba(37, 99, 235, 0.75)",
        row=1, col=1
    )

    # 5. Volume colorido de acordo com o fechamento do dia (alta/baixa)
    volume_colors = [
        "#10b981" if close >= open_ else "#ef4444"
        for close, open_ in zip(hist['Close'], hist['Open'])
    ]

    fig.add_trace(
        go.Bar(
            x=hist.index,
            y=hist['Volume'],
            name="Volume",
            marker_color=volume_colors,
            opacity=0.75,
            showlegend=False
        ),
        row=2, col=1
    )

    # Configuração de layout profissional escuro
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#111827",
        paper_bgcolor="#0e1117",
        xaxis=dict(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridcolor="#1f2937",
            rangebreaks=[dict(bounds=["sat", "mon"])]
        ),
        xaxis2=dict(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridcolor="#1f2937",
            rangebreaks=[dict(bounds=["sat", "mon"])]
        ),
        yaxis=dict(
            title="Preço (R$)",
            showgrid=True,
            gridcolor="#1f2937",
            tickprefix="R$ ",
            side="right",
            autorange=True,
            fixedrange=False
        ),
        yaxis2=dict(
            title="Volume",
            showgrid=True,
            gridcolor="#1f2937",
            side="right"
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=12, color="#9ca3af")
        ),
        margin=dict(l=20, r=40, t=60, b=20),
        height=580,
        hovermode="x unified"
    )

    return fig
