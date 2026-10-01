from src.db import init_db


def test_schemas_are_well_formed():
    for schema in (init_db.RAW_YOUTUBE_SCHEMA, init_db.RAW_LETTERBOXD_SCHEMA, init_db.SILVER_SCHEMA):
        body = schema["$jsonSchema"]
        assert body["bsonType"] == "object"
        assert "_governance" in body["required"]
        assert set(body["required"]) <= set(body["properties"])


def test_init_indexes_is_idempotent(db):
    init_db.init_indexes(db)
    init_db.init_indexes(db)
    assert "comment_id_1" in db["raw_youtube"].index_information()
