from src.processing.sentiment import clean_text, detect_language, extract_aspects


def test_clean_text_keeps_text_around_html_links():
    raw = 'Great <a href="https://x.com/a">link</a> movie&#39;s <br>end! www.foo.com ok'
    assert clean_text(raw) == "Great link movie's end! ok"


def test_clean_text_does_not_swallow_text_between_tags():
    raw = 'before <a href="https://x.com">x</a> MIDDLE <b>bold</b> after'
    assert "MIDDLE" in clean_text(raw)


def test_clean_text_non_string():
    assert clean_text(None) == ""
    assert clean_text(42) == ""


def test_extract_aspects_whole_words_only():
    assert extract_aspects("the directed scenes were great") == ["directing"]
    assert extract_aspects("indirect reference") == []


def test_extract_aspects_bilingual_and_multiword():
    aspects = extract_aspects("Ottima regia e colonna sonora, peccato per il bianco e nero")
    assert set(aspects) == {"directing", "soundtrack", "visuals"}


def test_detect_language_short_text():
    assert detect_language("hi") == "unknown"


def test_split_clauses_on_sentences_and_contrast():
    from src.processing.sentiment import split_clauses

    assert split_clauses("Regia splendida ma colonna sonora noiosa.") == ["Regia splendida", "colonna sonora noiosa."]
    assert split_clauses("Great acting, but the plot is weak. Loved the music!") == [
        "Great acting", "the plot is weak.", "Loved the music!",
    ]
    assert split_clauses("Tutto in una frase senza contrasto") == ["Tutto in una frase senza contrasto"]


def test_split_clauses_keeps_parenthetical_connector_inside_clause():
    from src.processing.sentiment import split_clauses

    assert split_clauses("Amazing visuals. The soundtrack, however, was terrible.") == [
        "Amazing visuals.", "The soundtrack was terrible.",
    ]
    assert split_clauses("La colonna sonora, però, è pessima") == ["La colonna sonora è pessima"]
