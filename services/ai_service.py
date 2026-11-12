"""
Módulo de integração com a API Google Gemini (google-genai).
Suporta múltiplos modelos com detecção automática de capacidades e suporte ao Google AI Pro:
- gemini-3.5-flash-lite: 500 req/dia Free / Ilimitado Pro
- gemini-1.5-pro / gemini-3.8-pro: Modelos analíticos do Google AI Pro
- argon: Modelo experimental avançado Pro
- gemini-3.8-flash / gemini-3.6-flash
Disponibiliza diagnóstico preditivo estruturado e assistente conversacional sobre ativos.
"""

import json
import re
import time
import streamlit as st
from config import GEMINI_MODELS, CACHE_TTL_AI


def get_available_models(api_key: str = "") -> list[str]:
    """
    Retorna a lista de modelos disponíveis.
    Se o usuário informou uma API Key válida, tenta descobrir modelos ativos na conta
    (incluindo Pro e experimentais como argon), fazendo fallback para GEMINI_MODELS.
    """
    if not api_key or api_key == "sua_chave_aqui":
        return GEMINI_MODELS

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        discovered = []
        for m in client.models.list():
            # Extrai o nome do modelo (ex: models/gemini-1.5-pro -> gemini-1.5-pro)
            m_name = getattr(m, "name", str(m)).replace("models/", "").strip()
            # Filtra modelos de texto/geração relevantes
            if any(k in m_name.lower() for k in ["gemini", "argon"]) and not any(k in m_name.lower() for k in ["vision-deprecated", "embedding", "aqa"]):
                discovered.append(m_name)
        
        if discovered:
            # Garante que os modelos preferenciais apareçam no topo
            ordered = [m for m in GEMINI_MODELS if m in discovered]
            extras = [m for m in discovered if m not in ordered]
            return ordered + extras if ordered else discovered
    except Exception:
        pass

    return GEMINI_MODELS


@st.cache_data(ttl=CACHE_TTL_AI, show_spinner=False)
def gerar_analise_cached(
    ticker: str,
    dados_mercado_str: str,
    titulos_noticias_str: str,
    api_key: str,
    modelo_preferencial: str = None
) -> dict:
    """
    Executa a análise preditiva via Gemini com cache de 30 minutos (1800s).
    Tenta os modelos na ordem configurada em GEMINI_MODELS com fallback automático.
    Aplica ThinkingConfig apenas nos modelos que suportam (3.8-flash, 3.6-flash).
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise Exception("A biblioteca 'google-genai' não está instalada. Execute: pip install google-genai")
    
    if not api_key or api_key == "sua_chave_aqui":
        raise Exception("Chave da API do Gemini (GEMINI_API_KEY) não configurada. Defina no arquivo .env ou na barra lateral.")

    prompt = f"""Atue como analista sênior de renda variável da B3. Analise o ativo {ticker}.
DADOS DE MERCADO: {dados_mercado_str}
MANCHETES RECENTES:
{titulos_noticias_str}

Retorne OBRIGATORIAMENTE e EXCLUSIVAMENTE um objeto JSON estrito com o seguinte esquema:
{{
  "tendencia": "ALTA" | "BAIXA" | "NEUTRA",
  "confianca_pct": 80,
  "resumo_executivo": "Texto direto em 2 frases sobre o panorama do ativo.",
  "principais_motivos": ["Motivo 1", "Motivo 2", "Motivo 3"],
  "variaveis_chave": ["Variável Macro 1", "Variável Macro 2", "Variável Macro 3"]
}}
"""

    modelo = modelo_preferencial if modelo_preferencial in GEMINI_MODELS else GEMINI_MODELS[0]
    
    # Inicializa o client preferencialmente com v1beta para compatibilidade total com gemini-3.8-flash
    try:
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    except Exception:
        client = genai.Client(api_key=api_key)

    # Modelos que suportam ThinkingConfig (desativar reasoning mode para ser mais rápido)
    # gemini-3.5-flash-lite, 1.5-pro e argon NÃO requerem thinking_config
    MODELOS_COM_THINKING = {"gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.8-pro"}

    # Lista de modelos a tentar: o preferencial primeiro, depois os fallbacks do config
    modelos_a_tentar = [modelo]
    for m in GEMINI_MODELS:
        if m != modelo:
            modelos_a_tentar.append(m)

    delays_503 = [1.5, 3.0]
    ultimo_erro = None
    tentativas_503 = 0

    for modelo_atual in modelos_a_tentar:

        # Monta a config correta de acordo com o suporte do modelo
        config_args = {
            "response_mime_type": "application/json",
            "temperature": 0.1,
            "max_output_tokens": 350,
        }
        if modelo_atual in MODELOS_COM_THINKING and hasattr(types, "ThinkingConfig"):
            try:
                config_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            except Exception:
                pass

        fast_config = types.GenerateContentConfig(**config_args)

        for tentativa in range(3):
            try:
                response = client.models.generate_content(
                    model=modelo_atual,
                    contents=prompt,
                    config=fast_config
                )
                raw_text = response.text.strip()

                # Limpar eventuais blocos de código markdown
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    raw_text = raw_text.strip()

                parsed = json.loads(raw_text)
                parsed["modelo_utilizado"] = modelo_atual
                return parsed

            except Exception as e:
                ultimo_erro = e
                err_upper = str(e).upper()

                # 503 / UNAVAILABLE: faz backoff e retenta o mesmo modelo
                if "503" in err_upper or "UNAVAILABLE" in err_upper:
                    if tentativas_503 < len(delays_503):
                        time.sleep(delays_503[tentativas_503])
                        tentativas_503 += 1
                        continue
                    # Esgotou as tentativas 503 para este modelo → tenta o próximo
                    break

                # 400 INVALID_ARGUMENT: modelo não suporta algum parâmetro → tenta o próximo
                if "400" in err_upper or "INVALID_ARGUMENT" in err_upper:
                    break

                # 404 NOT_FOUND: modelo indisponível → tenta o próximo
                if "404" in err_upper or "NOT_FOUND" in err_upper:
                    break

                # Se foi erro de versão de API (v1 vs v1beta), tenta via v1beta
                if "VERSION V1" in err_upper:
                    try:
                        alt_client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
                        alt_resp = alt_client.models.generate_content(
                            model=modelo_atual,
                            contents=prompt,
                            config=fast_config
                        )
                        raw_text = alt_resp.text.strip()
                        if raw_text.startswith("```"):
                            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                            raw_text = re.sub(r"\s*```$", "", raw_text)
                            raw_text = raw_text.strip()
                        parsed = json.loads(raw_text)
                        parsed["modelo_utilizado"] = modelo_atual
                        return parsed
                    except Exception as alt_err:
                        ultimo_erro = alt_err
                    break

                # Outros erros inesperados: interrompe tudo
                break

    # Mensagem final clara e orientativa
    if "503" in str(ultimo_erro).upper() or "UNAVAILABLE" in str(ultimo_erro).upper():
        raise Exception(
            f"Os modelos do Gemini estão enfrentando um pico de alta demanda (Erro 503). "
            f"Aguarde alguns segundos e clique em '🔄 Atualizar Análise (Limpar Cache)' na barra lateral."
        )

    raise Exception(f"Erro ao consultar o modelo '{modelo_atual}': {ultimo_erro}")


def consultar_ia_sobre_ativo(
    ticker: str,
    company_name: str,
    pergunta_usuario: str,
    dados_mercado_str: str,
    titulos_noticias_str: str,
    tendencia_atual_str: str,
    api_key: str,
    modelo_preferencial: str = None
) -> dict:
    """
    Consulta o modelo Gemini (incluindo opções do Google AI Pro como gemini-1.5-pro,
    gemini-3.8-pro e argon) para responder a dúvidas personalizadas sobre o ativo.
    O prompt inclui previamente o contexto técnico do gráfico, as notícias e a tendência.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise Exception("A biblioteca 'google-genai' não está instalada. Execute: pip install google-genai")

    if not api_key or api_key == "sua_chave_aqui":
        raise Exception("Chave da API do Gemini não configurada.")

    modelo = modelo_preferencial if modelo_preferencial in GEMINI_MODELS else GEMINI_MODELS[0]

    try:
        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
    except Exception:
        client = genai.Client(api_key=api_key)

    prompt = f"""Você é um analista financeiro sênior especializado no mercado acionário brasileiro (B3).
O investidor está acompanhando a ação {ticker} ({company_name}) e fez a seguinte pergunta:

❓ PERGUNTA DO INVESTIDOR:
"{pergunta_usuario}"

Considere obrigatoriamente os seguintes dados em tempo real para embasar sua resposta:

📊 CONTEXTO DO GRÁFICO E INDICADORES TÉCNICOS:
{dados_mercado_str}

📈 TENDÊNCIA PROJETADA ATUAL:
{tendencia_atual_str}

📰 MANCHETES DE NOTÍCIAS RECENTES:
{titulos_noticias_str}

DIRETRIZES DA RESPOSTA:
1. Responda diretamente à dúvida do investidor em tom profissional, objetivo e fundamentado.
2. Relacione explicitamente a pergunta com o comportamento do gráfico (médias móveis MMA 9/21, suportes ou variações recentes) e o cenário das notícias.
3. Destaque pontos de atenção, riscos e possíveis catalisadores para o ativo.
4. Use formatação limpa em tópicos com negritos para facilitar a leitura.
"""

    modelos_tentativa = [modelo] + [m for m in GEMINI_MODELS if m != modelo]
    ultimo_erro = None
    MODELOS_COM_THINKING = {"gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.8-pro"}

    for m_atual in modelos_tentativa:
        config_args = {
            "temperature": 0.4,
            "max_output_tokens": 1000,
        }
        # Adiciona thinking_config SOMENTE nos modelos que comprovadamente suportam
        if m_atual in MODELOS_COM_THINKING and hasattr(types, "ThinkingConfig"):
            try:
                config_args["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            except Exception:
                pass

        model_config = types.GenerateContentConfig(**config_args)

        try:
            resp = client.models.generate_content(
                model=m_atual,
                contents=prompt,
                config=model_config
            )
            raw_text = resp.text.strip() if resp.text else "Não foi possível gerar uma resposta detalhada."
            return {
                "resposta": raw_text,
                "modelo_utilizado": m_atual
            }
        except Exception as e:
            ultimo_erro = e
            continue

    raise Exception(f"Erro ao obter resposta da IA: {ultimo_erro}")
