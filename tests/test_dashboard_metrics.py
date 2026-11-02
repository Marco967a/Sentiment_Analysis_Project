from src.dashboard import metrics


def _silver(i, platform, label, score, aspects, published_at=None):
    return {
        "original_text": "t",
        "cleaned_text": "t",
        "sentiment_score": score,
        "sentiment_label": label,
        "language": "en",
        "aspects": aspects,
        "published_at": published_at,
        "_governance": {"source_platform": platform, "source_id": str(i), "extraction_timestamp": "x"},
    }


def test_gold_metrics_and_filters(db):
    db["silver_data"].insert_many([
        _silver(1, "youtube", "Positive", 0.8, ["plot", "acting"]),
        _silver(2, "youtube", "Negative", -0.4, ["plot"]),
        _silver(3, "letterboxd", "Positive", 0.6, []),
    ])
    m = metrics.get_gold_metrics(db)
    assert {d["_id"]: d["count"] for d in m["sentiment"]} == {"Positive": 2, "Negative": 1}
    assert m["aspects"][0]["_id"] == "plot" and m["aspects"][0]["count"] == 2
    assert abs(m["avg_score"][0]["average"] - 0.3333) < 1e-3

    only_yt = metrics.get_gold_metrics(db, {"_governance.source_platform": "youtube"})
    assert sum(d["count"] for d in only_yt["sentiment"]) == 2
    assert metrics.get_filter_options(db) == (["letterboxd", "youtube"], ["acting", "plot"])


def test_gold_metrics_empty(db):
    m = metrics.get_gold_metrics(db)
    assert m["sentiment"] == [] and m["aspects"] == []
    # Mongo reale restituisce [] qui, mongomock [{"average": None}]: l'app gestisce entrambi.
    assert all(d.get("average") is None for d in m["avg_score"])


def test_feed_orders_by_published_at(db):
    db["silver_data"].insert_many([
        _silver(1, "youtube", "Positive", 0.1, [], "2024-01-01"),
        _silver(2, "youtube", "Positive", 0.1, [], "2024-06-01"),
        _silver(3, "youtube", "Positive", 0.1, [], None),
    ])
    ids = [d["_governance"]["source_id"] for d in metrics.get_filtered_documents(db)]
    assert ids == ["2", "1", "3"]


def test_aspect_metrics_use_per_aspect_sentiment_with_legacy_fallback(db):
    mixed = _silver(1, "youtube", "Positive", 0.2, ["directing", "soundtrack"])
    mixed["aspect_sentiments"] = [
        {"aspect": "directing", "sentiment_score": 0.9, "sentiment_label": "Positive"},
        {"aspect": "soundtrack", "sentiment_score": -0.7, "sentiment_label": "Negative"},
    ]
    legacy = _silver(2, "youtube", "Negative", -0.5, ["soundtrack"])
    db["silver_data"].insert_many([mixed, legacy])

    by_aspect = {d["_id"]: d for d in metrics.get_gold_metrics(db)["aspects"]}
    assert by_aspect["directing"]["avg_score"] == 0.9
    assert by_aspect["soundtrack"]["count"] == 2
    assert abs(by_aspect["soundtrack"]["avg_score"] - (-0.6)) < 1e-9
    assert by_aspect["soundtrack"]["negative"] == 2 and by_aspect["soundtrack"]["positive"] == 0
