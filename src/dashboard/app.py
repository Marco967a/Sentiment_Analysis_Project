import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# `streamlit run src/dashboard/app.py` (anche su Streamlit Cloud) non mette la root del repo in sys.path:
# serve solo qui, perché questo è l'unico file lanciato come script e non come modulo (-m).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.dashboard.metrics import get_filter_options, get_filtered_documents, get_gold_metrics
from src.db.client import get_sync_db

CACHE_TTL_SECONDS = 60

st.set_page_config(page_title="Social Listening & Sentiment Hub", layout="wide", page_icon="🎬")

st.title("🎬 Sentiment Analysis & Social Listening Hub")
st.caption("Architettura Medallion & Data Governance con MongoDB, NLP multilingue e Aspect Extraction")


# Il parametro con prefisso "_" è escluso dall'hashing di Streamlit; la chiave di cache sono i filtri.
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def cached_filter_options(_db):
    return get_filter_options(_db)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def cached_metrics(_db, platform: str, aspect: str):
    return get_gold_metrics(_db, build_filter(platform, aspect))


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def cached_feed(_db, platform: str, aspect: str, limit: int):
    return get_filtered_documents(_db, build_filter(platform, aspect), limit=limit)


def build_filter(platform: str, aspect: str) -> dict:
    query = {}
    if platform != "Tutte":
        query["_governance.source_platform"] = platform
    if aspect != "Tutti":
        query["aspects"] = aspect
    return query


def main():
    try:
        db = get_sync_db()
        db.command("ping")
    except Exception as e:
        st.error(f"❌ Impossibile connettersi a MongoDB: {e}")
        st.warning(
            "Se stai eseguendo l'app su **Streamlit Cloud**, assicurati di configurare l'URI del database "
            "(ad esempio un cluster MongoDB Atlas) nella sezione **App settings -> Secrets**:\n\n"
            "```toml\n"
            "MONGODB_URI = \"mongodb+srv://<username>:<password>@cluster.mongodb.net/\"\n"
            "MONGODB_DB_NAME = \"sentiment_db\"\n"
            "```\n\n"
            "Se invece sei in locale, assicurati che il container MongoDB sia attivo (`docker compose up -d mongodb`)."
        )
        return

    st.sidebar.header("🔍 Filtri di Analisi")
    available_platforms, available_aspects = cached_filter_options(db)
    selected_platform = st.sidebar.selectbox("Piattaforma:", ["Tutte"] + available_platforms)
    selected_aspect = st.sidebar.selectbox("Aspetto del Film (Topic):", ["Tutti"] + available_aspects)
    if st.sidebar.button("🔄 Aggiorna dati"):
        st.cache_data.clear()
        st.rerun()

    metrics = cached_metrics(db, selected_platform, selected_aspect)
    sentiment_counts = metrics["sentiment"]
    avg_score = metrics["avg_score"]
    aspect_metrics = metrics["aspects"]
    language_counts = metrics["languages"]

    total_docs = sum(item["count"] for item in sentiment_counts)

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric(label="Totale Contributi Analizzati", value=total_docs)
    with col_kpi2:
        if avg_score and avg_score[0].get("average") is not None:
            st.metric(label="Sentiment Score Medio", value=f"{avg_score[0]['average']:+.2f}")
        else:
            st.metric(label="Sentiment Score Medio", value="N/A")
    with col_kpi3:
        top_aspect = aspect_metrics[0]["_id"] if aspect_metrics else "Nessuno"
        st.metric(label="Aspetto Più Discusso", value=top_aspect.capitalize())

    st.markdown("---")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📊 Distribuzione del Sentiment")
        if sentiment_counts:
            df_sent = pd.DataFrame(sentiment_counts).rename(columns={"_id": "Sentiment", "count": "Volume"})
            order = {"Positive": 0, "Neutral": 1, "Negative": 2}
            df_sent = df_sent.sort_values("Sentiment", key=lambda s: s.map(order))
            st.bar_chart(df_sent.set_index("Sentiment"), color="#29b5e8")
        else:
            st.info("Nessun dato per i filtri selezionati.")

    with col_g2:
        st.subheader("🎯 Aspect-Based Listening (Argomenti Trattati)")
        if aspect_metrics:
            df_asp = pd.DataFrame(aspect_metrics).rename(columns={"_id": "Aspetto", "count": "Menzioni"})
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
            df_asp_score = pd.DataFrame(aspect_metrics).rename(
                columns={"_id": "Aspetto", "avg_score": "Score Medio (da -1 a 1)"}
            )
            st.dataframe(
                df_asp_score[["Aspetto", "Score Medio (da -1 a 1)"]], use_container_width=True, hide_index=True
            )
        else:
            st.write("Nessun dato.")

    st.markdown("---")
    st.subheader("💬 Feed Commenti & Recensioni (Silver Layer Validato)")
    recent_docs = cached_feed(db, selected_platform, selected_aspect, 20)

    if recent_docs:
        df_feed = pd.DataFrame([{
            "Piattaforma": d.get("_governance", {}).get("source_platform", "").upper(),
            "Data": (d.get("published_at") or "")[:10] or "-",
            "Lingua": d.get("language", "N/A"),
            "Sentiment": d.get("sentiment_label"),
            "Score": round(d.get("sentiment_score", 0), 2),
            "Aspetti": ", ".join(d.get("aspects", [])) if d.get("aspects") else "-",
            "Testo": d.get("cleaned_text"),
        } for d in recent_docs])
        st.dataframe(df_feed, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun commento trovato per questi criteri.")


if __name__ == "__main__":
    main()
