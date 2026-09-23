import streamlit as st
import pandas as pd
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.db.client import get_sync_db

# Configurazione base della pagina Streamlit
st.set_page_config(page_title="Social Listening Dashboard", layout="wide")

st.title("Sentiment Analysis & Social Listening Dashboard")

def get_gold_metrics(db):
    """
    Esegue pipeline di aggregazione su MongoDB per ottenere le metriche 'Gold'.
    """
    silver_col = db["silver_data"]
    
    # Aggregazione per label di sentiment
    sentiment_counts = list(silver_col.aggregate([
        {"$group": {"_id": "$sentiment_label", "count": {"$sum": 1}}}
    ]))
    
    # Aggregazione per piattaforma sorgente
    platform_counts = list(silver_col.aggregate([
        {"$group": {"_id": "$_governance.source_platform", "count": {"$sum": 1}}}
    ]))

    # Score medio
    avg_score = list(silver_col.aggregate([
        {"$group": {"_id": None, "average": {"$avg": "$sentiment_score"}}}
    ]))

    return sentiment_counts, platform_counts, avg_score

def get_recent_documents(db, limit=10):
    silver_col = db["silver_data"]
    docs = list(silver_col.find().sort("_governance.extraction_timestamp", -1).limit(limit))
    return docs

def main():
    try:
        db = get_sync_db()
        st.success("Connesso al database MongoDB")
    except Exception as e:
        st.error(f"Errore di connessione al database: {e}")
        return

    st.header("Metriche Globali (Livello Gold)")
    
    sentiment_counts, platform_counts, avg_score = get_gold_metrics(db)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Distribuzione Sentiment")
        if sentiment_counts:
            df_sent = pd.DataFrame(sentiment_counts).rename(columns={"_id": "Sentiment", "count": "Totale"})
            st.bar_chart(df_sent.set_index("Sentiment"))
        else:
            st.write("Nessun dato disponibile.")

    with col2:
        st.subheader("Fonti Dati")
        if platform_counts:
            df_plat = pd.DataFrame(platform_counts).rename(columns={"_id": "Piattaforma", "count": "Totale"})
            st.bar_chart(df_plat.set_index("Piattaforma"))
        else:
            st.write("Nessun dato disponibile.")
            
    with col3:
        st.subheader("Score Medio Globale")
        if avg_score and avg_score[0].get("average") is not None:
            score = avg_score[0]["average"]
            st.metric(label="Sentiment Score (-1 a 1)", value=f"{score:.2f}")
        else:
            st.write("N/A")

    st.header("Ultimi Commenti Analizzati")
    recent_docs = get_recent_documents(db)
    
    if recent_docs:
        # Prepara un dataframe per la visualizzazione tabellare
        df_docs = pd.DataFrame([{
            "Testo Pulito": d.get("cleaned_text"),
            "Sentiment": d.get("sentiment_label"),
            "Score": d.get("sentiment_score"),
            "Fonte": d.get("_governance", {}).get("source_platform"),
            "Data": d.get("_governance", {}).get("extraction_timestamp")
        } for d in recent_docs])
        st.dataframe(df_docs, use_container_width=True)
    else:
        st.info("Nessun commento ancora analizzato e salvato nel livello Silver.")

if __name__ == "__main__":
    main()

