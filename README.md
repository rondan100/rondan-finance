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

## 🏷️ Histórico de Versões & Changelog

O projeto adota o padrão **Semantic Versioning 2.0** (`v{MAJOR}.{MINOR}.{PATCH}`):
- **`MAJOR` (Principal):** Mudanças estruturais de grande porte ou alterações de arquitetura.
- **`MINOR` (Recursos):** Novas funcionalidades relevantes mantendo compatibilidade retroativa.
- **`PATCH` (Correções):** Correções de bugs, ajustes finos e melhorias pontuais de performance.

| Versão | Data | Status | Tipo | Destaques Principais |
| :---: | :---: | :---: | :---: | :--- |
| **`v1.5.0`** | `Nov/2026` | 🟢 **Atual** | `MINOR` | Checklist quantitativo **CAN SLM** adaptado para a B3, força relativa vs Ibovespa (`^BVSP`) e integração enxuta no prompt da IA |
| **`v1.4.1`** | `Nov/2026` | ⚪ Estável | `PATCH` | Streaming em tempo real (resposta em ~300ms), corte de tokens, ativos clicáveis no Radar B3 e disparo direto |
| **`v1.4.0`** | `Nov/2026` | ⚪ Estável | `MINOR` | Suporte ao Google AI Pro (modelos Pro e `argon`), barra de pesquisa/chat com IA contextualizada com gráfico e notícias |
| **`v1.3.0`** | `Nov/2026` | ⚪ Estável | `MINOR` | Radar B3 (Scanner de oportunidades/compra), Cotação de hoje no Candlestick e correção de candles zerados |
| **`v1.2.0`** | `Nov/2026` | ⚪ Estável | `MINOR` | Integração Gemini 3.5 Flash Lite (500 req/dia), cotas dinâmicas e Enum de ativos B3 |
| **`v1.1.0`** | `Nov/2026` | ⚪ Estável | `MINOR` | Disparo de IA sob demanda por botão, cache de 30min e otimização drástica de tokens |
| **`v1.0.0`** | `Nov/2026` | ⚪ Inicial | `MAJOR` | Lançamento inicial da arquitetura modular, Candlestick interativo e Feed RSS |

<details open>
<summary><b>🔍 Detalhes das Alterações por Versão</b></summary>

### [`v1.5.0`] — Atual
- **Adicionado:** **Análise Quantitativa CAN SLM com Duplo Perfil de Rigor (`Calibrado B3` vs `Estrito Livro O'Neil`)** em `services/market_data.py`:
  - **M (Market Direction — Peso Principal via `^BVSP` `2y`):** Calcula **MM50** e **MM200** sobre 2 anos do Ibovespa (`fetch_ibov_data()` cacheado por 1h) e classifica o regime em `ALTA` (`^BVSP > MM50 e MM200`), `ATENCAO` (entre `MM50` e `MM200`) ou `BAIXA` (`^BVSP < MM50 e MM200`), exibido em banner de destaque no topo do card.
  - **C (Current Earnings):** Crescimento trimestral do lucro/LPA YoY $> 12\%$ no modo **Calibrado B3** ou $> 20\%$ no modo **Estrito O'Neil**.
  - **A (Annual Earnings):** No modo **Estrito O'Neil**, exige `CAGR Anual > 25%` E `ROE >= 17%`; no modo **Calibrado B3**, aprova com `(CAGR > 15% e ROE >= 14%)` OU `(ROE >= 17% e CAGR > 5%)`.
  - **N (New High):** Proximidade da máxima de 52 semanas (`>= 0.80` / até 20% abaixo do topo no **Calibrado B3**, ou `>= 0.85` / até 15% no **Estrito O'Neil**).
  - **S (Supply & Demand — Janela de 5 pregões):** Analisa os últimos 5 pregões e aprova se houver pelo menos 1 pregão de alta (`Close > Open` ou `Close > PrevClose`) com `Volume >= 1.25x` a média móvel de volume de 20 dias (`Pico Vol 5d`).
  - **L (Leader or Laggard — Janela fixa de 63 pregões / 3M):** Compara a variação percentual do ativo contra o `^BVSP` nos últimos 63 pregões (~3 meses), invariante ao período selecionado no gráfico.
- **Adicionado:** Seletor rápido `Perfil de Rigor CAN SLM` (`Calibrado B3` / `Estrito Livro (O'Neil)`) e componente visual responsivo `render_canslim_card` em `ui/components.py` com banner do Regime de Mercado (**M**) no topo, placar dos 5 critérios da ação (**C-A-N-S-L**) e detalhamento expansível (`✅`, `⚠️`, `➖ N/D`).
- **Adicionado:** Integração do **Score Quantitativo CAN SLM (`C-A-N-S-L`) no Radar B3** (`scan_b3_market_opportunities` em paralelo via `ThreadPoolExecutor` e `render_scanner_results`), adicionando a aba `🏆 Top Score CAN SLM`, pílulas visuais de critérios por ativo e ranqueamento híbrido (Técnico + CAN SLM).
- **Otimizado:** Injeção compacta da `summary_line` do CAN SLM dentro de `metrics["summary_line"]` para enriquecer o diagnóstico do Gemini com impacto mínimo de tokens.

### [`v1.4.1`]
- **Adicionado:** **Ativos Clicáveis no Radar B3**: Botão "📊 Analisar" em cada card de oportunidade, permitindo carregar o ativo instantaneamente no Dashboard principal com sincronização automática do seletor da barra lateral.
- **Adicionado:** **Streaming em Tempo Real (token a token)** via `st.write_stream`: a resposta começa a aparecer na tela em ~300ms com efeito de digitação ao vivo, eliminando telas travadas ou spinners demorados.
- **Adicionado:** Suporte à **varredura completa de todos os 44 ativos da B3** cadastrados em `config.py` com seletor de abrangência (*Todos os 44 Ativos* ou *Top 20 Mais Líquidos*).
- **Otimizado:** Prompt cirúrgico e redução de `max_output_tokens` para 220 tokens (~80 palavras diretas), acelerando o término da resposta em até 5x.
- **Corrigido:** Disparo e execução direta da IA ao clicar nos botões de sugestões rápidas (removido bloqueio do formulário `st.form`).
- **Corrigido:** Renderização em Markdown puro nativo (`st.markdown`) para evitar que quebras de linha e formatações da IA fossem engolidas por tags HTML.
- **Corrigido:** Montagem dinâmica de `GenerateContentConfig` por modelo, prevenindo erro `400 INVALID_ARGUMENT` em modelos Pro/Argon que não aceitam `thinking_config`.
- **Adicionado:** Botão "🗑️ Limpar Conversa" para resetar o histórico de perguntas do ativo na sessão.

### [`v1.4.0`]
- **Adicionado:** Suporte oficial a assinaturas **Google AI Pro** e modelos analíticos avançados: `gemini-1.5-pro`, `gemini-3.8-pro`, `argon` (experimental) e opção de digitar modelos customizados.
- **Adicionado:** Descoberta dinâmica de modelos habilitados na conta do usuário via `client.models.list()`.
- **Adicionado:** **Assistente Interativo de Consulta com IA**: Barra de pesquisa/chat onde o investidor faz perguntas diretas sobre o ativo selecionado. O modelo recebe automaticamente o contexto técnico do gráfico (preço, MMA 9/21, extremos), as últimas notícias do Google News e o diagnóstico de tendência.
- **Adicionado:** Botões com chips rápidos de perguntas frequentes (Médias móveis, Impacto de notícias, Dividendos e Riscos).

### [`v1.3.0`]
- **Adicionado:** **Radar B3 / Scanner de Oportunidades**: Botão e painel interativo para escanear automaticamente as principais ações da bolsa com tendência de compra (MMA 9 > MMA 21 com fluxo comprador) e ativos interessantes para "ficar de olho" (em rompimento/reversão).
- **Adicionado:** Destaque visual da **Cotação de Hoje** no gráfico Candlestick através de linha horizontal tracejada (`hline`) estilizada com o valor mais recente e data formatada.
- **Corrigido:** Sanitização e filtro de dados em `market_data.py` para eliminar candles zerados ou com anomalias de spread que ocorrem após o fechamento do pregão ou em horários noturnos no `yfinance`.
- **Adicionado:** Seção e tabela padronizada de versionamento no `README.md`.

### [`v1.2.0`]
- **Adicionado:** Modelo **`gemini-3.5-flash-lite`** como padrão oficial, elevando a cota gratuita de 20 para **500 requisições diárias**.
- **Corrigido:** Tratamento condicional de `thinking_config`, evitando erro `400 INVALID_ARGUMENT` em modelos que não suportam desativação de raciocínio prolongado.
- **Adicionado:** Enum de ativos populares da B3 (`PopularB3Asset`) com suporte a código personalizado (`OUTRO`).
- **Modificado:** Informação de cota diária (RPD) calculada dinamicamente por modelo na interface.

### [`v1.1.0`]
- **Modificado:** Chamadas à API Gemini agora são acionadas estritamente sob demanda via botão (`⚡ Gerar Diagnóstico com IA`).
- **Adicionado:** Persistência dos resultados da IA em `st.session_state` e cache de 30 minutos via `@st.cache_data`.
- **Otimizado:** Prompt enxuto com apenas 4 manchetes concisas, reduzindo o consumo de ~3.4k para ~800 tokens e acelerando a resposta.

### [`v1.0.0`]
- **Adicionado:** Estrutura modular em camadas (`services/`, `ui/`, `app.py`, `config.py`).
- **Adicionado:** Gráfico Candlestick com médias móveis MMA 9 e MMA 21 e volume financeiro.
- **Adicionado:** Feed de notícias integrado com Google News via RSS.
</details>

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
