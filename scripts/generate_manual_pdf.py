#!/usr/bin/env python3
"""
Script per la generazione del Manuale Utente del Social Listening & Sentiment Hub
in formato PDF professionale ad alta risoluzione tramite ReportLab.
Formattazione a 7 pagine perfettamente bilanciate ed eleganti (zero glifi mancanti).
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 46
MARGIN_Y = 48
USABLE_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)

class NumberedCanvas(canvas.Canvas):
    """
    Canvas a due passaggi per calcolare dinamicamente il numero totale di pagine
    e applicare header e footer professionali su ogni pagina tranne la copertina.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        if self._pageNumber == 1:
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(colors.HexColor("#1E3A8A"))
        self.drawString(MARGIN_X, PAGE_HEIGHT - 32, "SENTIMENT ANALYSIS & SOCIAL LISTENING HUB")

        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 32, "Manuale Utente & Guida Operativa End-to-End")

        # Linea divisoria header
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(MARGIN_X, PAGE_HEIGHT - 36, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 36)

        # Linea divisoria footer
        self.line(MARGIN_X, 40, PAGE_WIDTH - MARGIN_X, 40)

        # Footer
        self.drawString(MARGIN_X, 28, "Architettura Medallion • MongoDB 6.0 • Transformers RoBERTa • Streamlit")
        page_str = f"Pagina {self._pageNumber} di {total_pages}"
        self.drawRightString(PAGE_WIDTH - MARGIN_X, 28, page_str)

        self.restoreState()


def build_pdf(filename="docs/Manuale_Utente_Sentiment_Hub.pdf"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y
    )

    styles = getSampleStyleSheet()

    # Palette Cromatica Professionale
    c_navy = colors.HexColor("#1E3A8A")       # Blue 900
    c_accent = colors.HexColor("#2563EB")     # Blue 600
    c_dark = colors.HexColor("#0F172A")       # Slate 900
    c_body = colors.HexColor("#1E293B")       # Slate 800
    c_gray = colors.HexColor("#475569")       # Slate 600
    c_light_bg = colors.HexColor("#F8FAFC")   # Slate 50
    c_border = colors.HexColor("#CBD5E1")     # Slate 300
    c_code_bg = colors.HexColor("#0F172A")    # Dark slate
    c_code_txt = colors.HexColor("#F8FAFC")

    # Tipografia Curata
    styles.add(ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=25,
        leading=30,
        textColor=c_navy,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11.5,
        leading=16,
        textColor=c_gray,
        spaceAfter=18
    ))

    styles.add(ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12.5,
        textColor=c_dark
    ))

    styles.add(ParagraphStyle(
        'CoverMetaBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12.5,
        textColor=c_navy
    ))

    styles.add(ParagraphStyle(
        'DocH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13.5,
        leading=16.5,
        textColor=c_navy,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'DocH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=c_accent,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.8,
        textColor=c_body,
        alignment=TA_JUSTIFY,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.5,
        textColor=c_body,
        leftIndent=12,
        spaceAfter=3
    ))

    styles.add(ParagraphStyle(
        'CodeText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=c_code_txt
    ))

    styles.add(ParagraphStyle(
        'CalloutTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.8,
        leading=11.5,
        textColor=c_navy,
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.3,
        leading=11.5,
        textColor=c_body
    ))

    styles.add(ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=c_body,
        alignment=TA_LEFT
    ))

    styles.add(ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=c_navy,
        alignment=TA_LEFT
    ))

    def make_callout(tag, title, text, bg_hex="#F0FDF4", border_hex="#16A34A"):
        p_title = Paragraph(f"<b>[{tag.upper()}] &nbsp; {title}</b>", styles['CalloutTitle'])
        p_text = Paragraph(text, styles['CalloutText'])
        tbl = Table([[p_title], [p_text]], colWidths=[USABLE_WIDTH])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg_hex)),
            ('BOX', (0, 0), (-1, -1), 0.7, colors.HexColor(border_hex)),
            ('LINELEFT', (0, 0), (-1, -1), 3.5, colors.HexColor(border_hex)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return tbl

    def make_code_box(code_lines):
        paragraphs = [Paragraph(line.replace(" ", "&nbsp;"), styles['CodeText']) for line in code_lines]
        tbl = Table([[p] for p in paragraphs], colWidths=[USABLE_WIDTH])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), c_code_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, c_border),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        return tbl

    story = []

    # ==========================================
    # PAGINA 1: COPERTINA PROFESSIONALE
    # ==========================================
    story.append(Spacer(1, 20))
    badge_data = [[Paragraph("<b>DOCUMENTAZIONE UFFICIALE & GUIDA OPERATIVA END-TO-END</b>", ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=8, textColor=c_accent))]]
    t_badge = Table(badge_data, colWidths=[USABLE_WIDTH])
    t_badge.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_badge)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Sentiment Analysis &<br/>Social Listening Hub", styles['CoverTitle']))
    story.append(Paragraph(
        "Piattaforma Enterprise di Social Listening, Deep Learning NLP e Data Governance per l'Industria Cinematografica e dei Media",
        styles['CoverSubtitle']
    ))
    story.append(HRFlowable(width="100%", thickness=2.5, color=c_accent, spaceBefore=0, spaceAfter=14))

    meta_content = [
        [Paragraph("<b>Progetto:</b>", styles['CoverMetaBold']), Paragraph("Sentiment Analysis & Social Listening Hub", styles['CoverMeta'])],
        [Paragraph("<b>Architettura Dati:</b>", styles['CoverMetaBold']), Paragraph("Medallion Architecture (Bronze, Silver, Gold Layers)", styles['CoverMeta'])],
        [Paragraph("<b>Database & Storage:</b>", styles['CoverMetaBold']), Paragraph("MongoDB 6.0 con JSON Schema Validation e Indici Idempotenti", styles['CoverMeta'])],
        [Paragraph("<b>Modello NLP:</b>", styles['CoverMetaBold']), Paragraph("Twitter-RoBERTa-Base (Cardiff NLP) • LangDetect • Aspect Mining", styles['CoverMeta'])],
        [Paragraph("<b>Dashboard Web:</b>", styles['CoverMetaBold']), Paragraph("Streamlit 1.32+ con metriche Gold aggregate e filtri reattivi", styles['CoverMeta'])],
        [Paragraph("<b>Sorgenti Supportate:</b>", styles['CoverMetaBold']), Paragraph("YouTube Data API v3 (Trailer/Video) • Letterboxd BeautifulSoup Scraper (Recensioni)", styles['CoverMeta'])],
        [Paragraph("<b>Versione Documento:</b>", styles['CoverMetaBold']), Paragraph("1.0 (Guida Ufficiale di Riferimento)", styles['CoverMeta'])],
        [Paragraph("<b>Data Rilascio:</b>", styles['CoverMetaBold']), Paragraph(datetime.now().strftime("%B %Y"), styles['CoverMeta'])],
    ]
    t_meta = Table(meta_content, colWidths=[125, USABLE_WIDTH - 125])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_light_bg),
        ('BOX', (0, 0), (-1, -1), 0.8, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, c_border),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>Indice dei Capitoli</b>", styles['DocH2']))
    index_bullets = [
        "<b>Capitolo 1:</b> Visione Generale & Valore Strategico della Piattaforma",
        "<b>Capitolo 2:</b> Architettura Medallion & Pilastri di Data Governance (Bronze, Silver, Gold)",
        "<b>Capitolo 3:</b> Requisiti di Sistema, Configurazione `.env` & Avvio dei Container",
        "<b>Capitolo 4:</b> Inizializzazione Database, JSON Schema Validation & Indici Idempotenti",
        "<b>Capitolo 5:</b> Pipeline di Ingestione Dati (YouTube Data API v3 & Letterboxd Scraper)",
        "<b>Capitolo 6:</b> Pipeline NLP & Arricchimento Silver (RoBERTa, 5 Aspetti Tematici, Lingue)",
        "<b>Capitolo 7:</b> Guida Operativa alla Dashboard Streamlit & Analitiche Gold",
        "<b>Capitolo 8:</b> Risoluzione dei Problemi, Manutenzione & FAQ Operative"
    ]
    for b in index_bullets:
        story.append(Paragraph(f"• &nbsp; {b}", styles['DocBullet']))

    story.append(PageBreak())

    # ==========================================
    # PAGINA 2: CAPITOLO 1 & CAPITOLO 2
    # ==========================================
    story.append(Paragraph("1. Visione Generale & Valore Strategico", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "Il <b>Sentiment Analysis & Social Listening Hub</b> è una piattaforma progettata per intercettare, "
        "strutturare ed elaborare le reazioni del pubblico e della critica cinematografica. Nel mercato dell'intrattenimento, "
        "il sentiment generato sui canali social in occasione dell'uscita di trailer, teaser o anteprime influisce in maniera determinante "
        "sul passaparola e sul box office. Questo sistema fornisce strumenti quantitativi e qualitativi per monitorare "
        "in modo oggettivo l'accoglienza di qualsiasi film, serie TV o franchise multimediale.",
        styles['DocBody']
    ))
    story.append(Paragraph("I punti cardine che contraddistinguono la soluzione includono:", styles['DocBody']))
    story.append(Paragraph("• <b>Rigore di Data Governance:</b> conservazione integrale del lineage di provenienza e validazione dello schema al momento della scrittura nel database.", styles['DocBullet']))
    story.append(Paragraph("• <b>Aspect-Based Social Listening:</b> scomposizione del sentiment su 5 dimensioni verticali dell'opera (Regia, Cast, Colonna Sonora, Visivo/Estetica, Sceneggiatura/Trama).", styles['DocBullet']))
    story.append(Paragraph("• <b>Multi-Sorgente Complementare:</b> convergenza tra piattaforme ad altissimo coinvolgimento di massa (YouTube) e community specializzate di appassionati e critici (Letterboxd).", styles['DocBullet']))

    story.append(Spacer(1, 4))
    story.append(Paragraph("2. Architettura Medallion & Data Governance", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "I dati fluiscono attraverso un'architettura <b>Medallion</b> suddivisa in tre livelli logici su MongoDB:",
        styles['DocBody']
    ))

    arch_table_data = [
        [Paragraph("Livello", styles['TableHeader']), Paragraph("Collezione / Entità", styles['TableHeader']), Paragraph("Descrizione & Scopo", styles['TableHeader']), Paragraph("Governance & Integrità", styles['TableHeader'])],
        [
            Paragraph("<b>BRONZE</b><br/>(Raw Data)", styles['TableCellBold']),
            Paragraph("<code>raw_youtube</code><br/><code>raw_letterboxd</code>", styles['TableCell']),
            Paragraph("Ingestione dei dati grezzi così come estratti dalle API o dallo scraping DOM.", styles['TableCell']),
            Paragraph("• Indice univoco anti-duplicato<br/>• Metadati <code>_governance</code><br/>• Flag <code>processed: False</code>", styles['TableCell'])
        ],
        [
            Paragraph("<b>SILVER</b><br/>(Enriched)", styles['TableCellBold']),
            Paragraph("<code>silver_data</code>", styles['TableCell']),
            Paragraph("Dati ripuliti, normalizzati, arricchiti con score sentiment continuo [-1.0, +1.0], label, lingua e aspetti tematici.", styles['TableCell']),
            Paragraph("• Strict JSON Schema Validation<br/>• Indice univoco source_platform + source_id<br/>• Indici su aspetti e lingua", styles['TableCell'])
        ],
        [
            Paragraph("<b>GOLD</b><br/>(Analytics)", styles['TableCellBold']),
            Paragraph("Pipeline <code>$group</code> &<br/>Dashboard Streamlit", styles['TableCell']),
            Paragraph("Aggregazioni analitiche, KPI sintetici e visualizzazione interattiva dei dati per decision-maker e analisti.", styles['TableCell']),
            Paragraph("• Query performanti indicizzate<br/>• Lettura read-only analitica<br/>• Audit trail completo", styles['TableCell'])
        ]
    ]
    t_arch = Table(arch_table_data, colWidths=[65, 95, 175, 168])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_navy),
        ('BOX', (0, 0), (-1, -1), 0.7, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_arch)

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "GOVERNANCE",
        "I Tre Pilastri della Data Governance",
        "<b>1. Data Lineage:</b> ogni documento Silver contiene <code>source_platform</code>, <code>source_id</code> ed <code>extraction_timestamp</code>.<br/>"
        "<b>2. JSON Schema Validation:</b> MongoDB respinge record privi di sentiment score, testo o label corrette.<br/>"
        "<b>3. Idempotenza:</b> logiche di upsert prevengono duplicati e mantengono lo stato di elaborazione.",
        "#EFF6FF", "#2563EB"
    ))

    story.append(PageBreak())

    # ==========================================
    # PAGINA 3: CAPITOLO 3 & CAPITOLO 4
    # ==========================================
    story.append(Paragraph("3. Requisiti di Sistema & Avvio dell'Ambiente", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "<b>Prerequisiti:</b> Linux (Ubuntu consigliato), macOS o Windows WSL2 • Python 3.11+ • Docker 24+ con plugin Compose v2 • 4 GB RAM.",
        styles['DocBody']
    ))
    story.append(Paragraph("<b>File di Configurazione Ambiente (<code>.env</code>):</b>", styles['DocBody']))
    env_code = [
        "MONGODB_URI=mongodb://root:example_password@localhost:27017/",
        "MONGODB_DB_NAME=sentiment_db",
        "YOUTUBE_API_KEY=AIzaSyBcsZVJ0ZVJqq-ESEMPIO_API_KEY",
        "TRANSFORMERS_MODEL=cardiffnlp/twitter-roberta-base-sentiment-latest"
    ]
    story.append(make_code_box(env_code))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Modalità di Esecuzione Disponibili", styles['DocH2']))
    story.append(Paragraph("• <b>Modalità Docker Completa (Consigliata):</b> avvia MongoDB, Mongo Express e Dashboard Streamlit:", styles['DocBody']))
    story.append(make_code_box(["docker compose up -d"]))
    story.append(Paragraph("• <b>Modalità Ibrida (Sviluppo Locale):</b> avvia solo il database in Docker ed esegue gli script in virtualenv:", styles['DocBody']))
    story.append(make_code_box([
        "docker compose up -d mongodb",
        "source venv/bin/activate && pip install -r requirements.txt"
    ]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("4. Inizializzazione Database, Schema & Indici", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "Prima di effettuare qualunque ingestione o analisi, è necessario inizializzare il database eseguendo:",
        styles['DocBody']
    ))
    story.append(make_code_box(["python src/db/init_db.py"]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Operazioni Eseguite da `init_db.py`", styles['DocH2']))
    story.append(Paragraph("• <b>Creazione Collezioni Bronze:</b> inizializza <code>raw_youtube</code> e <code>raw_letterboxd</code>.", styles['DocBullet']))
    story.append(Paragraph("• <b>Schema di Validazione Rigoroso per <code>silver_data</code>:</b> impone la presenza di <code>original_text</code>, <code>cleaned_text</code>, <code>sentiment_score</code> (double compreso tra -1.0 e 1.0), <code>sentiment_label</code> (Positive, Negative, Neutral) e del blocco <code>_governance</code> completo.", styles['DocBullet']))
    story.append(Paragraph("• <b>Creazione Indici Univoci di Idempotenza:</b>", styles['DocBullet']))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;1. <code>raw_youtube.comment_id</code> (univoco: blocca inserimenti multipli dello stesso commento).", styles['DocBullet']))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;2. <code>raw_letterboxd.film + author</code> (univoco: una sola recensione per autore per film).", styles['DocBullet']))
    story.append(Paragraph("&nbsp;&nbsp;&nbsp;&nbsp;3. <code>silver_data.source_platform + source_id</code> (univoco: garantisce tracciabilità e lineage privo di doppioni).", styles['DocBullet']))
    story.append(Paragraph("• <b>Indici di Performance:</b> indicizzazione di <code>aspects</code>, <code>language</code> e <code>_governance.processed</code>.", styles['DocBullet']))

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "ATTENZIONE",
        "Regola di Robustezza dello Schema",
        "La validazione schema opera a livello di motore MongoDB. Se un record presenta campi non conformi, viene rigettato con <code>DocumentFailedValidation</code>, preservando la pulizia del layer Silver.",
        "#FFFBEB", "#D97706"
    ))

    story.append(PageBreak())

    # ==========================================
    # PAGINA 4: CAPITOLO 5
    # ==========================================
    story.append(Paragraph("5. Pipeline di Ingestione Dati (Bronze Layer)", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "Il layer Bronze raccoglie i dati esterni preservandoli fedelmente. Include due client pronti all'uso:",
        styles['DocBody']
    ))

    story.append(Paragraph("5.1 Ingestione YouTube Data API v3 (`src/ingestion/youtube.py`)", styles['DocH2']))
    story.append(Paragraph(
        "Interroga i thread di commenti associati a uno o più video YouTube (trailer ufficiali, teaser, video-recensioni), "
        "ordinandoli per rilevanza per massimizzare la qualità del feedback estratto.",
        styles['DocBody']
    ))
    story.append(Paragraph("<b>Funzionalità e Architettura:</b>", styles['DocBody']))
    story.append(Paragraph("• <b>Paginazione Automatica:</b> supporta il superamento del limite dei 100 commenti per pagina tramite <code>pageToken</code>.", styles['DocBullet']))
    story.append(Paragraph("• <b>Campi Estratti:</b> <code>video_id</code>, <code>video_title</code>, <code>comment_id</code>, <code>author</code>, <code>text</code>, <code>like_count</code>, <code>published_at</code> e metadati <code>_governance</code>.", styles['DocBullet']))
    story.append(Paragraph("• <b>Upsert Idempotente:</b> aggiorna i metadati esistenti (es. like) senza resettare il flag di elaborazione <code>processed</code>.", styles['DocBullet']))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Esempio di Esecuzione e Codice Python:</b>", styles['DocBody']))
    story.append(make_code_box([
        "# Esecuzione da terminale",
        "python src/ingestion/youtube.py",
        "",
        "# Utilizzo come modulo per qualsiasi film/video:",
        "from src.ingestion.youtube import get_youtube_comments, save_to_bronze",
        "dati = get_youtube_comments(video_id='XXXXXX', max_results=100, video_title='Trailer 1')",
        "save_to_bronze(dati)"
    ]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("5.2 Scraper Letterboxd (`src/ingestion/letterboxd.py`)", styles['DocH2']))
    story.append(Paragraph(
        "Esegue lo scraping etico delle recensioni degli utenti cinefili da Letterboxd utilizzando <code>BeautifulSoup4</code>, "
        "adattandosi alla struttura moderna del DOM (<code>article.production-viewing</code>).",
        styles['DocBody']
    ))
    story.append(Paragraph("<b>Funzionalità e Architettura:</b>", styles['DocBody']))
    story.append(Paragraph("• <b>Navigazione Pagine:</b> itera tra le pagine di recensioni ordinate per attività recente.", styles['DocBullet']))
    story.append(Paragraph("• <b>Campi Estratti:</b> <code>film</code> (slug), <code>author</code>, <code>rating</code> in stelle (es. ★★★★), <code>text</code> e <code>_governance.raw_url</code>.", styles['DocBullet']))
    story.append(Paragraph("• <b>Deduplicazione:</b> chiave composta <code>film + author</code> per garantire unicità della voce.", styles['DocBullet']))

    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>Esempio di Esecuzione e Codice Python:</b>", styles['DocBody']))
    story.append(make_code_box([
        "# Esecuzione da terminale",
        "python src/ingestion/letterboxd.py",
        "",
        "# Utilizzo come modulo per qualsiasi film (slug URL):",
        "from src.ingestion.letterboxd import scrape_letterboxd_reviews, save_to_bronze",
        "recensioni = scrape_letterboxd_reviews(film_slug='the-matrix', max_pages=3)",
        "save_to_bronze(recensioni)"
    ]))

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "NOTA",
        "Come identificare lo slug di Letterboxd",
        "Lo slug è la parte finale dell'indirizzo del film su Letterboxd. Ad esempio per <code>https://letterboxd.com/film/dune-part-two/</code> lo slug è <code>dune-part-two</code>.",
        "#F8FAFC", "#64748B"
    ))

    story.append(PageBreak())

    # ==========================================
    # PAGINA 5: CAPITOLO 6
    # ==========================================
    story.append(Paragraph("6. Pipeline NLP & Arricchimento (Silver Layer)", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "Il modulo <code>src/processing/sentiment.py</code> orchestra l'elaborazione NLP. Recupera ciclicamente a batch "
        "i record non ancora processati (<code>_governance.processed != True</code>), applica quattro stadi di arricchimento "
        "e li salva con upsert nella collezione <code>silver_data</code>:",
        styles['DocBody']
    ))
    story.append(make_code_box(["python src/processing/sentiment.py"]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("I Quattro Stadi della Pipeline NLP", styles['DocH2']))

    nlp_phases = [
        [Paragraph("Stadio", styles['TableHeader']), Paragraph("Strumento / Metodo", styles['TableHeader']), Paragraph("Dettaglio del Trattamento", styles['TableHeader'])],
        [
            Paragraph("1. Data Cleaning", styles['TableCellBold']),
            Paragraph("Espressioni Regolari (Regex)", styles['TableCell']),
            Paragraph("Rimozione di link URL, tag HTML residui, simboli non convenzionali e compressione degli spazi bianchi multipli.", styles['TableCell'])
        ],
        [
            Paragraph("2. Language Detection", styles['TableCellBold']),
            Paragraph("<code>langdetect</code>", styles['TableCell']),
            Paragraph("Riconoscimento automatico del codice lingua ISO (es. <code>it</code>, <code>en</code>, <code>es</code>, <code>de</code>) con seed fissato per riproducibilità.", styles['TableCell'])
        ],
        [
            Paragraph("3. Aspect Mining", styles['TableCellBold']),
            Paragraph("Pattern Matching bilingue (IT/EN)", styles['TableCell']),
            Paragraph("Ricerca di keyword tematiche per attribuire ciascun commento a uno o più argomenti del vocabolario cinematografico.", styles['TableCell'])
        ],
        [
            Paragraph("4. Sentiment Scoring", styles['TableCellBold']),
            Paragraph("Transformer RoBERTa<br/>(Cardiff NLP)", styles['TableCell']),
            Paragraph("Inferenza Deep Learning con mappatura su score continuo [-1.0, +1.0] e classificazione in Positive, Neutral, Negative.", styles['TableCell'])
        ]
    ]
    t_nlp = Table(nlp_phases, colWidths=[85, 115, 303])
    t_nlp.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_navy),
        ('BOX', (0, 0), (-1, -1), 0.7, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_nlp)

    story.append(Spacer(1, 5))
    story.append(Paragraph("Tassonomia delle 5 Dimensioni di Aspect-Based Listening", styles['DocH2']))
    story.append(Paragraph("• <b>directing (Regia):</b> regia, cineasta, filmmaker, visione registica, ritmo dell'opera.", styles['DocBullet']))
    story.append(Paragraph("• <b>acting (Recitazione / Cast):</b> interpretazione, attori, cast, performance dei protagonisti.", styles['DocBullet']))
    story.append(Paragraph("• <b>soundtrack (Colonna Sonora / Audio):</b> colonna sonora, brani musicali, sound design, compositore.", styles['DocBullet']))
    story.append(Paragraph("• <b>visuals (Estetica, Fotografia & CGI):</b> cinematografia, effetti speciali, estetica, cromie, bianco e nero.", styles['DocBullet']))
    story.append(Paragraph("• <b>plot (Trama & Sceneggiatura):</b> storia, script, dialoghi, sviluppo dei personaggi, finale.", styles['DocBullet']))

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "PIPELINE",
        "Batching Automatico & Audit Trail",
        "La funzione <code>process_unprocessed_data()</code> elabora tutti i documenti Bronze pendenti a blocchi da 100 fino a conclusione. Ciascun record Bronze viene marcato con <code>_governance.processed: True</code> e relativo timestamp UTC di audit.",
        "#EFF6FF", "#2563EB"
    ))

    story.append(PageBreak())

    # ==========================================
    # PAGINA 6: CAPITOLO 7
    # ==========================================
    story.append(Paragraph("7. Guida alla Dashboard Streamlit (Gold Layer)", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "Il layer Gold rende fruibili le analitiche attraverso un'applicazione web interattiva sviluppata in <b>Streamlit</b>. "
        "Le metriche non sono precalcolate staticamente, ma vengono aggregate al volo tramite pipeline MongoDB "
        "(<code>$match</code>, <code>$group</code>, <code>$avg</code>, <code>$unwind</code>), garantendo reattività immediata ai filtri.",
        styles['DocBody']
    ))

    story.append(Paragraph("Comando di Avvio", styles['DocH2']))
    story.append(make_code_box([
        "streamlit run src/dashboard/app.py",
        "# Accessibile all'URL: http://localhost:8501"
    ]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Struttura & Funzionalità dell'Interfaccia", styles['DocH2']))

    ui_table_data = [
        [Paragraph("Modulo Interfaccia", styles['TableHeader']), Paragraph("Descrizione & Operatività Utente", styles['TableHeader'])],
        [
            Paragraph("<b>KPI Header Cards</b>", styles['TableCellBold']),
            Paragraph("<b>1. Volume Totale:</b> conteggio dei contributi analizzati.<br/><b>2. Sentiment Medio:</b> score continuo aggregato da -1.0 a +1.0.<br/><b>3. Top Aspect:</b> l'aspetto più discusso dal pubblico (es. Acting o Visuals).", styles['TableCell'])
        ],
        [
            Paragraph("<b>Sidebar Filtri Reattivi</b>", styles['TableCellBold']),
            Paragraph("Filtri combinabili che ricalcolano tutte le viste in tempo reale:<br/>• <b>Piattaforma:</b> Tutte, solo YouTube, solo Letterboxd.<br/>• <b>Aspetto Tematico:</b> Tutti o focus su singola dimensione (Directing, Acting, Soundtrack, Visuals, Plot).<br/>• <b>Lingua:</b> Selezione per codice ISO (Inglese, Italiano, ecc.).", styles['TableCell'])
        ],
        [
            Paragraph("<b>Visualizzazioni Analitiche</b>", styles['TableCellBold']),
            Paragraph("• <b>Distribuzione Sentiment:</b> conteggio suddiviso per Positive, Neutral e Negative.<br/>• <b>Gradimento per Aspetto:</b> confronto dello score medio tra le 5 aree tematiche.<br/>• <b>Ripartizione Lingue & Canali:</b> metriche di penetrazione geografica e di canale.", styles['TableCell'])
        ],
        [
            Paragraph("<b>Social Feed Interattivo</b>", styles['TableCellBold']),
            Paragraph("Feed cronologico dei commenti completi di badge identificativi:<br/>• Origine (YouTube o Letterboxd)<br/>• Score normalizzato e classificazione (es. +0.78 Positive)<br/>• Badge lingua e tag tematici associati.", styles['TableCell'])
        ]
    ]
    t_ui = Table(ui_table_data, colWidths=[120, 383])
    t_ui.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_navy),
        ('BOX', (0, 0), (-1, -1), 0.7, c_border),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_light_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_ui)

    story.append(Spacer(1, 4))
    story.append(make_callout(
        "SUGGERIMENTO",
        "Analisi Mirata delle Dimensioni Critiche",
        "Combinando il filtro 'Aspetto Tematico' (es. <code>soundtrack</code>) con la piattaforma (es. <code>youtube</code>), è possibile isolare immediatamente i commenti specifici per valutare il gradimento delle musiche o del cast.",
        "#F0FDF4", "#16A34A"
    ))

    story.append(PageBreak())

    # ==========================================
    # PAGINA 7: CAPITOLO 8 & CONCLUSIONI
    # ==========================================
    story.append(Paragraph("8. Risoluzione Problemi, Manutenzione & FAQ", styles['DocH1']))
    story.append(HRFlowable(width="100%", thickness=1, color=c_accent, spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("<b>D: Errore 'Connection refused' su porta 27017 (MongoDB).</b>", styles['DocH2']))
    story.append(Paragraph(
        "<b>R:</b> Il server MongoDB non è attivo. Avviarlo con <code>docker compose up -d mongodb</code> oppure verificare con <code>docker ps</code> se il container è in stato 'Up'.",
        styles['DocBody']
    ))

    story.append(Paragraph("<b>D: Errore 'permission denied while trying to connect to the docker API at unix:///var/run/docker.sock'.</b>", styles['DocH2']))
    story.append(Paragraph(
        "<b>R:</b> Su Linux l'utente deve appartenere al gruppo docker. Eseguire <code>sudo usermod -aG docker $USER</code> seguito da <code>newgrp docker</code> (oppure riavviare la sessione). In alternativa, anteporre <code>sudo</code> ai comandi docker.",
        styles['DocBody']
    ))

    story.append(Paragraph("<b>D: Conflitto di container ('Conflict. The container name is already in use').</b>", styles['DocH2']))
    story.append(Paragraph(
        "<b>R:</b> È presente un container con lo stesso nome da una sessione precedente. Rimuoverlo con <code>docker rm -f sentiment_mongodb</code> e riavviare con <code>docker compose up -d mongodb</code>.",
        styles['DocBody']
    ))

    story.append(Paragraph("<b>D: Come gestire i limiti di quota di YouTube Data API v3?</b>", styles['DocH2']))
    story.append(Paragraph(
        "<b>R:</b> Google fornisce gratuitamente 10.000 unità al giorno per progetto. Ogni chiamata a <code>commentThreads.list</code> richiede solo 1 unità di quota e preleva fino a 100 commenti. È quindi possibile raccogliere fino a 1.000.000 di commenti al giorno a costo zero.",
        styles['DocBody']
    ))

    story.append(Paragraph("<b>D: Errore 'Document failed validation' durante l'inserimento in Silver.</b>", styles['DocH2']))
    story.append(Paragraph(
        "<b>R:</b> Il documento non rispetta le regole imposte dallo schema (es. score fuori dal range [-1.0, 1.0] o assenza del lineage di governance). Lo schema protegge l'integrità del database rifiutando il record malformato.",
        styles['DocBody']
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Best Practice di Manutenzione & Scalabilità", styles['DocH2']))
    story.append(Paragraph("• <b>Backup del Database:</b> eseguire dump periodici con <code>docker exec sentiment_mongodb mongodump --out /data/backup</code>.", styles['DocBullet']))
    story.append(Paragraph("• <b>Estensione Vocabolari:</b> aggiornare <code>ASPECT_KEYWORDS</code> in <code>src/processing/sentiment.py</code> per includere nuovi registi, attori o termini specifici del film in esame.", styles['DocBullet']))
    story.append(Paragraph("• <b>Integrazione Nuove Fonti:</b> definire nuove collection Bronze (es. <code>raw_imdb</code>) mantenendo il blocco <code>_governance</code> per preservare il lineage.", styles['DocBullet']))

    story.append(Spacer(1, 6))
    story.append(make_callout(
        "DOCUMENTAZIONE",
        "Supporto & Documentazione Tecnica di Progetto",
        "Per dettagli architetturali aggiuntivi, consultare il file <code>README.md</code> nella radice del progetto o la documentazione delle API nel repository ufficiale.",
        "#F8FAFC", "#475569"
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ Manuale PDF generato con successo in: {filename}")
    return filename

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "docs/Manuale_Utente_Sentiment_Hub.pdf"
    build_pdf(out_file)
