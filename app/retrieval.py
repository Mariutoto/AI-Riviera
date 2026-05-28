import json
import math
import re
from collections import Counter
from functools import lru_cache

from app.config import CHUNKS_PATH


STOPWORDS = {
    "alors", "avec", "aux", "ce", "ces", "dans", "de", "des", "du", "elle", "en", "est",
    "et", "il", "la", "le", "les", "leur", "mais", "ou", "où", "par", "pas", "plus",
    "pour", "que", "qui", "sur", "un", "une", "vous", "the", "and", "of", "to", "in",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


@lru_cache(maxsize=1)
def load_chunks() -> list[dict]:
    if not CHUNKS_PATH.exists():
        return []

    chunks = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                record = json.loads(line)
                record["_tokens"] = Counter(tokenize(record["text"]))
                chunks.append(record)
    return chunks


def search(query: str, limit: int = 6) -> list[dict]:
    query_tokens = Counter(tokenize(query))
    if not query_tokens:
        return []

    chunks = load_chunks()
    total_chunks = max(len(chunks), 1)
    document_frequency = Counter()
    for chunk in chunks:
        for token in chunk["_tokens"]:
            document_frequency[token] += 1

    scored = []
    for chunk in chunks:
        score = 0.0
        for token, query_count in query_tokens.items():
            term_count = chunk["_tokens"].get(token, 0)
            if not term_count:
                continue
            idf = math.log((1 + total_chunks) / (1 + document_frequency[token])) + 1
            score += query_count * (1 + math.log(term_count)) * idf

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

    results = []
    for score, chunk in scored[:limit]:
        result = dict(chunk)
        result.pop("_tokens", None)
        result["score"] = round(score, 3)
        results.append(result)
    return results
