# Sentiment Analysis & Social Listening Platform

Pipeline di Sentiment Analysis e Social Listening basata sull'architettura **Medallion (Bronze, Silver, Gold)**, con focus sulla **Data Governance** e storage su **MongoDB**.

Il sistema raccoglie dati da piattaforme social e di recensioni (YouTube e Letterboxd), arricchisce i testi tramite modelli **Transformer (NLP)** e offre dashboard analitiche per il monitoraggio dei trend.

---

## Architettura Dati & Governance

L'architettura segue il pattern a strati:
- **Bronze Layer (Raw Data):** Ingestione dei dati grezzi (`raw_youtube`, `raw_letterboxd`) tracciando il *Data Lineage* (provenienza, data/ora e payload originario).
- **Silver Layer (Cleaned & Enriched):** Pulizia del testo e inferenza del Sentiment con modello RoBERTa (`cardiffnlp/twitter-roberta-base-sentiment-latest`). I dati sono protetti da **MongoDB JSON Schema Validation** per garantire integrità e conformità dei campi.
- **Gold Layer (Aggregated Analytics):** Query di aggregazione MongoDB (`$group`, `$avg`) per calcolare metriche chiave esposte su Dashboard Web interattiva.

---

## Struttura del Progetto

```text
├── config/                  # Configurazioni di ambiente e costanti
├── src/
│   ├── db/
│   │   ├── client.py        # Client MongoDB sincrono e asincrono (Motor)
│   │   └── init_db.py       # Setup schema validation & collezioni
│   ├── ingestion/
│   │   ├── letterboxd.py    # Crawler/Scraper recensioni Letterboxd
│   │   └── youtube.py       # Client API YouTube v3 (ordinamento per rilevanza/like)
│   ├── processing/
│   │   └── sentiment.py     # Pulizia testo & pipeline NLP Hugging Face
│   └── dashboard/
│       └── app.py           # Dashboard analitica Streamlit
├── docker-compose.yml       # Configurazione MongoDB locale & Mongo Express
├── requirements.txt         # Dipendenze Python
└── .env.example             # Template variabili d'ambiente
```

---

## Setup & Installazione

### 1. Avvio Database MongoDB (Docker)

```bash
docker run -d --name sentiment_mongodb -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=root \
  -e MONGO_INITDB_ROOT_PASSWORD=example_password \
  -v sentiment_mongodb_data:/data/db \
  --restart unless-stopped mongo:6.0
```

### 2. Configurazione Ambiente Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Inizializzazione Schema & Data Governance

```bash
python src/db/init_db.py
```

### 4. Ingestione ed Elaborazione

- **Scraping Letterboxd:**
  ```bash
  python src/ingestion/letterboxd.py
  ```
- **Elaborazione Sentiment Analysis:**
  ```bash
  python src/processing/sentiment.py
  ```

### 5. Avvio Dashboard Streamlit

```bash
streamlit run src/dashboard/app.py
```
