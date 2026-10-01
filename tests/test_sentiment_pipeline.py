import pytest

from src.processing import sentiment


class FakeModel:
    def __init__(self, label="positive", score=0.9, fail_on=None):
        self.label, self.score, self.fail_on = label, score, fail_on

    def __call__(self, text, truncation=True):
        if self.fail_on and self.fail_on in text:
            raise ValueError("boom")
        return [{"label": self.label, "score": self.score}]


@pytest.fixture
def fake_model(monkeypatch):
    def install(model):
        monkeypatch.setattr(sentiment, "get_sentiment_pipeline", lambda: model)
    return install


def test_label_mapping(fake_model):
    fake_model(FakeModel("negative", 0.8))
    assert sentiment.analyze_sentiment("bad") == (-0.8, "Negative")
    fake_model(FakeModel("LABEL_2", 0.7))
    assert sentiment.analyze_sentiment("good") == (0.7, "Positive")
    fake_model(FakeModel("neutral", 0.6))
    assert sentiment.analyze_sentiment("meh") == (0.0, "Neutral")


def test_missing_pipeline_returns_none_not_fake_neutral(fake_model):
    fake_model(None)
    assert sentiment.analyze_sentiment("some text") is None


def test_process_requires_pipeline(fake_model, db):
    fake_model(None)
    with pytest.raises(RuntimeError):
        sentiment.process_unprocessed_data(db=db)


def _raw_yt(comment_id, text):
    return {
        "comment_id": comment_id,
        "text": text,
        "published_at": "2024-01-01T00:00:00Z",
        "_governance": {
            "source_platform": "youtube",
            "extraction_timestamp": "2024-01-02T00:00:00+00:00",
            "processed": False,
        },
    }


def test_processing_is_idempotent_and_marks_bronze(fake_model, db):
    fake_model(FakeModel())
    db["raw_youtube"].insert_many([_raw_yt("a", "great movie"), _raw_yt("b", "nice director")])

    sentiment.process_unprocessed_data(db=db)
    sentiment.process_unprocessed_data(db=db)

    assert db["silver_data"].count_documents({}) == 2
    silver = db["silver_data"].find_one({"_governance.source_id": "b"})
    assert silver["aspects"] == ["directing"]
    assert silver["model_name"] == sentiment.MODEL_NAME
    assert silver["cleaning_version"] == sentiment.CLEANING_VERSION
    assert silver["published_at"] == "2024-01-01T00:00:00Z"
    assert db["raw_youtube"].count_documents({"_governance.processed": True}) == 2


def test_failed_document_is_not_marked_and_does_not_block_others(fake_model, db):
    fake_model(FakeModel(fail_on="poison"))
    db["raw_youtube"].insert_many([_raw_yt("a", "poison pill"), _raw_yt("b", "fine")])

    sentiment.process_unprocessed_data(db=db)

    bad = db["raw_youtube"].find_one({"comment_id": "a"})
    assert bad["_governance"]["processed"] is False
    assert bad["_governance"]["attempts"] >= 1
    assert "error" in bad["_governance"]
    assert db["raw_youtube"].find_one({"comment_id": "b"})["_governance"]["processed"] is True
    assert db["silver_data"].count_documents({}) == 1


def test_documents_stop_being_retried_after_max_attempts(fake_model, db):
    fake_model(FakeModel(fail_on="poison"))
    db["raw_youtube"].insert_one(_raw_yt("a", "poison"))
    for _ in range(sentiment.MAX_ATTEMPTS + 2):
        sentiment.process_unprocessed_data(db=db)
    assert db["raw_youtube"].find_one({})["_governance"]["attempts"] == sentiment.MAX_ATTEMPTS

    sentiment.reset_failed(db)
    assert "attempts" not in db["raw_youtube"].find_one({})["_governance"]


def test_reprocess_outdated_silver(fake_model, db):
    fake_model(FakeModel("negative", 0.5))
    db["silver_data"].insert_one({
        "original_text": "great director",
        "cleaned_text": "old",
        "sentiment_score": 0.1,
        "sentiment_label": "Positive",
        "cleaning_version": 1,
        "model_name": "old-model",
        "_governance": {"source_platform": "test", "source_id": "1", "extraction_timestamp": "x"},
    })
    assert sentiment.reprocess_outdated_silver(db) == 1
    doc = db["silver_data"].find_one({})
    assert doc["sentiment_label"] == "Negative" and doc["aspects"] == ["directing"]
    assert sentiment.reprocess_outdated_silver(db) == 0


def test_letterboxd_legacy_docs_without_review_id_keep_old_source_id(fake_model, db):
    fake_model(FakeModel())
    db["raw_letterboxd"].insert_one({
        "film": "dune",
        "author": "bob",
        "text": "fine",
        "_governance": {"source_platform": "letterboxd", "processed": False},
    })
    sentiment.process_unprocessed_data(db=db)
    assert db["silver_data"].find_one({})["_governance"]["source_id"] == "dune#bob"
