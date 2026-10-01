from typing import Optional


def get_gold_metrics(db, filter_query: Optional[dict] = None) -> dict:
    """
    Metriche Gold calcolate con una sola aggregazione ($facet) sul livello Silver.
    Chiavi: sentiment, platforms, avg_score, aspects, languages (liste di documenti).
    """
    pipeline = []
    if filter_query:
        pipeline.append({"$match": filter_query})
    pipeline.append({"$facet": {
        "sentiment": [{"$group": {"_id": "$sentiment_label", "count": {"$sum": 1}}}],
        "platforms": [{"$group": {"_id": "$_governance.source_platform", "count": {"$sum": 1}}}],
        "avg_score": [{"$group": {"_id": None, "average": {"$avg": "$sentiment_score"}}}],
        "aspects": [
            {"$unwind": "$aspects"},
            {"$group": {"_id": "$aspects", "count": {"$sum": 1}, "avg_score": {"$avg": "$sentiment_score"}}},
            {"$sort": {"count": -1}},
        ],
        "languages": [
            {"$group": {"_id": "$language", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
        ],
    }})
    result = list(db["silver_data"].aggregate(pipeline))
    return result[0] if result else {
        "sentiment": [], "platforms": [], "avg_score": [], "aspects": [], "languages": [],
    }


def get_filtered_documents(db, filter_query: Optional[dict] = None, limit: int = 25) -> list[dict]:
    """Ultimi documenti Silver, ordinati per data originale del contenuto (poi per data di estrazione)."""
    cursor = db["silver_data"].find(filter_query or {}).sort([
        ("published_at", -1),
        ("_governance.extraction_timestamp", -1),
    ]).limit(limit)
    return list(cursor)


def get_filter_options(db) -> tuple[list[str], list[str]]:
    """Piattaforme e aspetti disponibili (esclusi None e stringhe vuote)."""
    silver = db["silver_data"]
    platforms = sorted(p for p in silver.distinct("_governance.source_platform") if isinstance(p, str) and p.strip())
    aspects = sorted(a for a in silver.distinct("aspects") if isinstance(a, str) and a.strip())
    return platforms, aspects
