# 📊 Dashboard Financeiro B3 com Análise IA (Gemini 3.5 Flash Lite)

Aplicação modular e interativa desenvolvida em **Python** e **Streamlit** para acompanhamento e análise técnica de ações da Bolsa Brasileira (**B3**), potencializada pela família de modelos **Gemini** (`google-genai`).

---

## 🏗️ Arquitetura Padronizada do Projeto

O projeto foi dividido em camadas de responsabilidade bem definidas para facilitar a manutenção e escalabilidade:

```
rondan-finance/
├── .env                     # Variáveis de ambiente (Chave GEMINI_API_KEY)
├── .env.example             # Modelo para configuração das variáveis
├── .gitignore               # Arquivos ignorados pelo Git
├── requirements.txt         # Dependências do projeto
├── README.md                # Documentação técnica
├── config.py                # Configurações globais, períodos, modelos e dicionário de ativos
│
├── services/                # Camada de integração com serviços e APIs externas
│   ├── __init__.py
│   ├── market_data.py       # Coleta yfinance, médias móveis (MMA9/21) e métricas OHLC
│   ├── news_service.py      # Extração de notícias RSS do Google News com feedparser
│   └── ai_service.py        # Integração com Gemini 3.8 Flash, cache e retry
│
├── ui/                      # Camada de apresentação e componentes visuais
│   ├── __init__.py
│   ├── styles.py            # Folhas de estilo CSS customizadas
│   ├── charts.py            # Construção do gráfico Candlestick interativo (Plotly)
│   └── components.py        # Métricas, cards dinâmicos de IA, colunas e notícias
│
└── app.py                   # Ponto de entrada (Main), orquestrador do Streamlit
```

---

## 🚀 Funcionalidades

1. **Barra Lateral com Enumeração de Ativos Populares da B3:**
   - Lista selecionável baseada em Enum (`PopularB3Asset`) com as ações mais negociadas da bolsa brasileira (ex: `PETR4.SA - Petrobras (PN)`, `VALE3.SA - Vale (ON)`, `ITUB4.SA - Itaú`, `BBAS3.SA - Banco do Brasil`, `WEGE3.SA - WEG`, etc.), com **PETR4.SA** como padrão inicial.
   - Opção `OUTRO` para digitar qualquer ticker personalizado da B3.
   - Seletor de período do gráfico (`1m`, `3m`, `6m`, `1y`).
   - Seletor dinâmico do modelo do Gemini e campo para chave de API.
   - Botão para limpar o cache de 30 minutos e forçar nova análise.

2. **Coleta de Dados e Indicadores (B3):**
   - Integração com `yfinance` para cotações e histórico completo OHLC.
   - Cálculo automático de médias móveis de **9** e **21** períodos (**MMA 9** e **MMA 21**).
   - Métricas no topo: Preço atual, variação diária absoluta (R$) e percentual (%), além da faixa do período.

3. **Gráfico Candlestick Interativo (`plotly.graph_objects`):**
   - Candlestick com candles verdes/vermelhos e MMA 9 e 21.
   - Ajuste de `rangebreaks` para ocultar os finais de semana sem pregão na B3.

4. **Feed de Notícias Automatizado:**
   - Extração das notícias mais recentes via RSS do Google News (`feedparser`) buscando pelo nome da empresa.

5. **Motor de Inteligência Artificial (Gemini — Família Flash):**
   - **Modelo Padrão:** `gemini-3.5-flash-lite` com **500 requisições/dia gratuitas** no Google AI Studio. Fallback automático para `gemini-3.8-flash` e `gemini-3.6-flash` (20 req/dia cada) em caso de erro.
   - **`thinking_config` condicional:** Apenas os modelos 3.8/3.6-flash recebem o parâmetro de desativação de raciocínio prolongado; o 3.5-flash-lite não o suporta e receberia erro 400 caso fosse enviado.
   - **Disparo sob Demanda (Via Botão):** A chamada da IA não roda automaticamente a cada clique ou ajuste da tela. É disparada exclusivamente quando o usuário clica no botão **⚡ Gerar Diagnóstico com IA**.
   - **Persistência na Sessão (`st.session_state`):** Uma vez gerado o diagnóstico para um ativo, ele permanece na tela mesmo que você mude o período do gráfico, dê zoom ou abra as notícias.
   - **Cache de 30 minutos (`@st.cache_data(ttl=1800)`):** Evita chamadas duplicadas para o mesmo ativo e período.
   - Retorno estruturado em **JSON estrito** com tendência (`ALTA`, `BAIXA`, `NEUTRA`), confiança (`confianca_pct`), resumo executivo em 2 frases, 3 principais motivos e variáveis macroeconômicas.

6. **Interface Moderna:**
   - Card com borda e iluminação dinâmica conforme a tendência (Verde para ALTA, Vermelho para BAIXA, Âmbar para NEUTRA).
   - Sanfona (`st.expander`) com as notícias originais e links diretos para leitura.

---

## 🛠️ Instalação e Execução

### 1. Criar o Ambiente Virtual e Instalar Dependências

```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar no Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Ou no Linux/macOS:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar a Chave do Gemini

Obtenha sua chave no [Google AI Studio](https://aistudio.google.com/) e adicione-a no arquivo `.env`:

```env
GEMINI_API_KEY=sua_chave_aqui
```

### 3. Executar o Dashboard

```bash
streamlit run app.py
```
