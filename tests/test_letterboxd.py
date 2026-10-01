from bs4 import BeautifulSoup

from src.ingestion import letterboxd

HTML = """
<ul>
<li class="film-detail" data-object-id="viewing:111">
  <a class="name">alice</a><span class="rating rated-7">★★★½</span>
  <time datetime="2024-03-01T10:00:00Z"></time>
  <div class="body-text">Loved it</div>
</li>
<li class="film-detail">
  <a class="context" href="/bob/film/dune/1/">link</a><a class="name">bob</a>
  <span class="rating">★★★★★</span><div class="body-text">Epic</div>
</li>
<li class="film-detail"><div class="body-text">anonymous, no id</div></li>
<li class="film-detail"><a class="name">carl</a><div class="body-text"></div></li>
</ul>
"""


def _span(html):
    return BeautifulSoup(html, "html.parser").span


def test_parse_reviews():
    reviews = letterboxd.parse_reviews(HTML, "dune", "http://u")
    assert [r["review_id"] for r in reviews] == ["viewing:111", "/bob/film/dune/1/"]
    assert reviews[0]["rating"] == 3.5 and reviews[1]["rating"] == 5.0
    assert reviews[0]["published_at"] == "2024-03-01T10:00:00Z"
    assert reviews[1]["published_at"] is None


def test_parse_rating_variants():
    assert letterboxd.parse_rating(_span('<span class="rating">★★½</span>')) == 2.5
    assert letterboxd.parse_rating(_span('<span class="rating">no rating</span>')) is None
    assert letterboxd.parse_rating(None) is None


def test_save_to_bronze_is_idempotent_and_keeps_processed_state(db):
    reviews = letterboxd.parse_reviews(HTML, "dune", "http://u")
    assert letterboxd.save_to_bronze(reviews, db=db) == (2, 0)
    db["raw_letterboxd"].update_many({}, {"$set": {"_governance.processed": True}})

    letterboxd.save_to_bronze(reviews, db=db)

    assert db["raw_letterboxd"].count_documents({}) == 2
    assert db["raw_letterboxd"].count_documents({"_governance.processed": True}) == 2
