"""
Módulo de estilos CSS personalizados para o Streamlit.
"""

import streamlit as st


def apply_custom_css():
    """
    Aplica regras de estilização CSS moderna e responsiva na aplicação.
    """
    st.markdown("""
    <style>
        /* Fundo e tipografia geral */
        .main {
            background-color: #0e1117;
        }
        
        /* Container de análise de IA - ALTA */
        .ai-card-alta {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(6, 78, 59, 0.25) 100%);
            border: 2px solid #10b981;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        }
        
        /* Container de análise de IA - BAIXA */
        .ai-card-baixa {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(127, 29, 29, 0.25) 100%);
            border: 2px solid #ef4444;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.2);
        }
        
        /* Container de análise de IA - NEUTRA */
        .ai-card-neutra {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(120, 53, 15, 0.25) 100%);
            border: 2px solid #f59e0b;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 0 20px rgba(245, 158, 11, 0.2);
        }

        /* Badges e Pílulas */
        .badge-pill {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 9999px;
            font-weight: 700;
            font-size: 0.95rem;
            letter-spacing: 0.5px;
        }
        .badge-alta {
            background-color: #10b981;
            color: #ffffff;
        }
        .badge-baixa {
            background-color: #ef4444;
            color: #ffffff;
        }
        .badge-neutra {
            background-color: #f59e0b;
            color: #ffffff;
        }
        .badge-confianca {
            background-color: #2563eb;
            color: #ffffff;
            margin-left: 8px;
        }
        .badge-model {
            background-color: #4b5563;
            color: #e5e7eb;
            font-size: 0.8rem;
            padding: 3px 10px;
            border-radius: 9999px;
            margin-left: 10px;
        }

        /* Itens de Motivos e Variáveis Macro */
        .reason-item {
            background-color: rgba(255, 255, 255, 0.05);
            border-left: 4px solid #38bdf8;
            padding: 12px 14px;
            margin-bottom: 10px;
            border-radius: 0 6px 6px 0;
            font-size: 0.95rem;
            color: #f3f4f6;
        }
        .macro-item {
            background-color: rgba(255, 255, 255, 0.05);
            border-left: 4px solid #a855f7;
            padding: 12px 14px;
            margin-bottom: 10px;
            border-radius: 0 6px 6px 0;
            font-size: 0.95rem;
            color: #f3f4f6;
        }
        
        /* Cartão de Notícia */
        .news-card {
            padding: 14px 18px;
            margin-bottom: 12px;
            border-radius: 8px;
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid #2d3748;
            transition: all 0.2s ease;
        }
        .news-card:hover {
            background-color: rgba(255, 255, 255, 0.07);
            border-color: #4a5568;
            transform: translateY(-1px);
        }
    </style>
    """, unsafe_allow_html=True)

