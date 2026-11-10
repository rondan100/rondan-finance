"""
Módulo de extração e processamento de notícias via RSS do Google News.
"""

import re
import urllib.parse
from datetime import datetime
import streamlit as st
import feedparser
from config import CACHE_TTL_NEWS, MAX_NEWS_TO_DISPLAY, MAX_NEWS_FOR_PROMPT


@st.cache_data(ttl=CACHE_TTL_NEWS, show_spinner=False)
def fetch_google_news(query: str, max_items: int = MAX_NEWS_TO_DISPLAY):
    """
    Extrai as últimas notícias do Google News via RSS com feedparser.
    """
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    
    feed = feedparser.parse(rss_url)
    items = []
    
    for entry in feed.entries[:max_items]:
        title = entry.get("title", "Sem título")
        link = entry.get("link", "#")
        published = entry.get("published", "")
        source = entry.get("source", {}).get("title", "Google News")
        
        # Limpar o nome da fonte no título se presente no final (ex: "Título - G1")
        clean_title = re.sub(r'\s*-\s*[^-]+$', '', title).strip()
        
        # Formatar data de publicação caso disponível
        formatted_date = published
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt = datetime(*entry.published_parsed[:6])
                formatted_date = dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            formatted_date = published

        items.append({
            "title": clean_title or title,
            "raw_title": title,
            "link": link,
            "published": formatted_date,
            "source": source
        })
        
    return items


def format_news_for_prompt(news_items: list, max_titles: int = 4) -> str:
    """
    Formata apenas os primeiros títulos de notícias para compor o prompt enxuto da IA,
    reduzindo o consumo de tokens e acelerando a resposta do modelo.
    """
    selected = news_items[:max_titles]
    if not selected:
        return "- Nenhuma notícia recente encontrada."
        
    return "\n".join([f"- {item['title'][:85]}" for item in selected])

