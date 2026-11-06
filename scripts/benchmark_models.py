"""Confronta modelli di sentiment sul campione etichettato tests/data/sentiment_eval.csv.

Uso: python scripts/benchmark_models.py [model_id ...]
Senza argomenti confronta il modello inglese e quello multilingue. Riporta accuracy e macro-F1 per lingua.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

from transformers import pipeline

DATASET = Path(__file__).resolve().parents[1] / "tests" / "data" / "sentiment_eval.csv"
DEFAULT_MODELS = [
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
    "cardiffnlp/twitter-xlm-roberta-base-sentiment",
]
LABELS = ["Negative", "Neutral", "Positive"]


def normalize(label: str) -> str:
    label = label.lower()
    if "neg" in label or label == "label_0":
        return "Negative"
    if "pos" in label or label == "label_2":
        return "Positive"
    return "Neutral"


def macro_f1(pairs) -> float:
    scores = []
    for cls in LABELS:
        tp = sum(1 for t, p in pairs if t == p == cls)
        fp = sum(1 for t, p in pairs if p == cls and t != cls)
        fn = sum(1 for t, p in pairs if t == cls and p != cls)
        scores.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(scores) / len(scores)


def main(models: list[str]) -> None:
    with open(DATASET, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for model_id in models:
        clf = pipeline("sentiment-analysis", model=model_id, tokenizer=model_id)
        by_lang = defaultdict(list)
        for row in rows:
            pred = normalize(clf(row["text"], truncation=True)[0]["label"])
            by_lang[row["language"]].append((row["label"], pred))
        print(f"\n{model_id}")
        for lang, pairs in sorted(by_lang.items()):
            acc = sum(t == p for t, p in pairs) / len(pairs)
            print(f"  {lang}: n={len(pairs)} accuracy={acc:.2f} macro-F1={macro_f1(pairs):.2f}")


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT_MODELS)
