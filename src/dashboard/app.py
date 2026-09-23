import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

st.set_page_config(page_title="Social Listening & Sentiment Hub", layout="wide", page_icon="🎬")

st.title("🎬 Sentiment Analysis & Social Listening Hub")
st.caption("Architettura Medallion & Data Governance con MongoDB, RoBERTa NLP e Aspect Extraction")

def get_gold_metrics(db, filter_query=None):
    """
    Esegue pipeline di aggregazione su MongoDB per ottenere le metriche di livello Gold.
    """
    silver_col = db["silver_data"]
    match_stage = [{"$match": filter_query}] if filter_query else []

    # 1. Distribuzione Sentiment
    sentiment_counts = list(silver_col.aggregate(match_stage + [
        {"$group": {"_id": "$sentiment_label", "count": {"$sum": 1}}}
    ]))
    
    # 2. Distribuzione Piattaforme
    platform_counts = list(silver_col.aggregate(match_stage + [
        {"$group": {"_id": "$_governance.source_platform", "count": {"$sum": 1}}}
    ]))

    # 3. Score Medio
    avg_score = list(silver_col.aggregate(match_stage + [
        {"$group": {"_id": None, "average": {"$avg": "$sentiment_score"}}}
    ]))

    # 4. Distribuzione Aspetti Tematici (Aspect-Based Listening)
    aspect_metrics = list(silver_col.aggregate(match_stage + [
        {"$unwind": "$aspects"},
        {"$group": {
            "_id": "$aspects",
            "count": {"$sum": 1},
            "avg_score": {"$avg": "$sentiment_score"}
        }},
        {"$sort": {"count": -1}}
    ]))

    # 5. Distribuzione Lingue
    language_counts = list(silver_col.aggregate(match_stage + [
        {"$group": {"_id": "$language", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))

    return sentiment_counts, platform_counts, avg_score, aspect_metrics, language_counts

def get_filtered_documents(db, filter_query=None, limit=25):
    silver_col = db["silver_data"]
    query = filter_query or {}
    docs = list(silver_col.find(query).sort("_governance.extraction_timestamp", -1).limit(limit))
    return docs

def main():
    try:
        db = get_sync_db()
    except Exception as e:
        st.error(f"Errore di connessione a MongoDB: {e}")
        return

    # Barra laterale dei filtri
    st.sidebar.header("🔍 Filtri di Analisi")
    
    # Recupero piattaforme e aspetti sanitizzati (escludendo None e stringhe vuote)
    raw_platforms = db["silver_data"].distinct("_governance.source_platform")
    available_platforms = sorted([p for p in raw_platforms if isinstance(p, str) and p.strip()])
    selected_platform = st.sidebar.selectbox("Piattaforma:", ["Tutte"] + available_platforms)

    raw_aspects = db["silver_data"].distinct("aspects")
    available_aspects = sorted([a for a in raw_aspects if isinstance(a, str) and a.strip()])
    selected_aspect = st.sidebar.selectbox("Aspetto del Film (Topic):", ["Tutti"] + available_aspects)

    # Costruzione query filtro MongoDB
    filter_query = {}
    if selected_platform != "Tutte":
        filter_query["_governance.source_platform"] = selected_platform
    if selected_aspect != "Tutti":
        filter_query["aspects"] = selected_aspect

    # Metriche Gold
    sentiment_counts, platform_counts, avg_score, aspect_metrics, language_counts = get_gold_metrics(db, filter_query)
    
    total_docs = sum(item["count"] for item in sentiment_counts) if sentiment_counts else 0

    # KPI Summary Cards
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric(label="Totale Contributi Analizzati", value=total_docs)
    with col_kpi2:
        if avg_score and avg_score[0].get("average") is not None:
            score = avg_score[0]["average"]
            st.metric(label="Sentiment Score Medio", value=f"{score:+.2f}", delta=f"{score:.2f}")
        else:
            st.metric(label="Sentiment Score Medio", value="N/A")
    with col_kpi3:
        top_aspect = aspect_metrics[0]["_id"] if aspect_metrics else "Nessuno"
        st.metric(label="Aspetto Più Discusso", value=top_aspect.capitalize())

    st.markdown("---")

    # Grafici Principali
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📊 Distribuzione del Sentiment")
        if sentiment_counts:
            df_sent = pd.DataFrame(sentiment_counts).rename(columns={"_id": "Sentiment", "count": "Volume"})
            st.bar_chart(df_sent.set_index("Sentiment"), color="#29b5e8")
        else:
            st.info("Nessun dato per i filtri selezionati.")

    with col_g2:
        st.subheader("🎯 Aspect-Based Listening (Argomenti Trattati)")
        if aspect_metrics:
            df_asp = pd.DataFrame(aspect_metrics).rename(columns={"_id": "Aspetto", "count": "Menzioni", "avg_score": "Score Medio"})
            st.bar_chart(df_asp.set_index("Aspetto")["Menzioni"], color="#ff4b4b")
        else:
            st.info("Nessun aspetto rilevato con i filtri attuali.")

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        st.subheader("🌐 Ripartizione per Lingua")
        if language_counts:
            df_lang = pd.DataFrame(language_counts).rename(columns={"_id": "Lingua", "count": "Totale"})
            st.dataframe(df_lang, use_container_width=True, hide_index=True)
        else:
            st.write("Nessun dato.")

    with col_g4:
        st.subheader("📌 Sentiment per Singolo Aspetto")
        if aspect_metrics:
            df_asp_score = pd.DataFrame(aspect_metrics).rename(columns={"_id": "Aspetto", "avg_score": "Score Medio (da -1 a 1)"})
            st.dataframe(df_asp_score[["Aspetto", "Score Medio (da -1 a 1)"]], use_container_width=True, hide_index=True)
        else:
            st.write("Nessun dato.")

    st.markdown("---")
    st.subheader("💬 Feed Commenti & Recensioni (Silver Layer Validato)")
    recent_docs = get_filtered_documents(db, filter_query, limit=20)
    
    if recent_docs:
        df_feed = pd.DataFrame([{
            "Piattaforma": d.get("_governance", {}).get("source_platform", "").upper(),
            "Lingua": d.get("language", "N/A"),
            "Sentiment": d.get("sentiment_label"),
            "Score": round(d.get("sentiment_score", 0), 2),
            "Aspetti": ", ".join(d.get("aspects", [])) if d.get("aspects") else "-",
            "Testo": d.get("cleaned_text")
        } for d in recent_docs])
        st.dataframe(df_feed, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun commento trovato per questi criteri.")

if __name__ == "__main__":
    main()
