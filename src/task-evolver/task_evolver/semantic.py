import json
import math
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .expansion import config_value, normalize_key
from .store import SOURCE_RANK


def unit_vector(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 4096:
        raise ValueError("invalid embedding dimensions")
    if any(
        type(value) not in (int, float) or not math.isfinite(value) for value in values
    ):
        raise ValueError("invalid embedding values")
    norm = math.hypot(*values)
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("invalid embedding norm")
    return [value / norm for value in values]


class OpenAIEmbeddings:
    def __init__(self, model=None, dotenv_path=None):
        dotenv = (
            Path(dotenv_path)
            if dotenv_path
            else Path(__file__).resolve().parents[3] / ".env"
        )
        self.model = model or config_value("TASK_EVOLVER_EMBEDDING_MODEL", dotenv)
        self.api_key = config_value("OPENAI_API_KEY", dotenv)

    def embed(self, keys):
        if not self.model or not self.api_key:
            raise ValueError("embedding model and API key are required")
        if not 1 <= len(keys) <= 129:
            raise ValueError("embedding batch must contain 1 to 129 keys")
        keys = [normalize_key(key) for key in keys]
        request = Request(
            "https://api.openai.com/v1/embeddings",
            data=json.dumps(
                {
                    "model": self.model,
                    "input": keys,
                    "encoding_format": "float",
                    "dimensions": 256,
                }
            ).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
        except HTTPError as exc:
            exc.close()
            raise RuntimeError(f"OpenAI embeddings returned HTTP {exc.code}") from None
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError("embedding response exceeds 2 MiB")
        data = json.loads(raw)["data"]
        if (
            not isinstance(data, list)
            or any(
                not isinstance(item, dict) or type(item.get("index")) is not int
                for item in data
            )
            or sorted(item["index"] for item in data) != list(range(len(keys)))
        ):
            raise ValueError("embedding indexes do not match inputs")
        return [
            unit_vector(item["embedding"])
            for item in sorted(data, key=lambda item: item["index"])
        ]


def lookup_details(evolver, key, embedder=None):
    key = normalize_key(key)
    importance = evolver.lookup(key)
    sources = {evolver.ref_key: "reference"}
    for pair in evolver.store.effective():
        for item in (pair.a_key, pair.b_key):
            if item != evolver.ref_key and SOURCE_RANK[pair.source] < SOURCE_RANK.get(
                sources.get(item), 3
            ):
                sources[item] = pair.source
    result = {
        "key": key,
        "importance": importance,
        "source": sources.get(key, "miss"),
        "estimated_importance": None,
        "candidates": [],
        "embedding_error": None,
    }
    if importance is not None:
        return result
    embedder = embedder or OpenAIEmbeddings()
    if not embedder.model:
        return result
    conn = evolver.table.conn
    scores = dict(
        conn.execute("SELECT key, importance FROM scores ORDER BY key LIMIT 128")
    )
    if not scores:
        return result
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS embedding_cache (model TEXT, key TEXT, vector TEXT NOT NULL, PRIMARY KEY (model, key))"
        )
        vectors = {}
        missing = []
        for candidate in [key, *scores]:
            row = conn.execute(
                "SELECT vector FROM embedding_cache WHERE model = ? AND key = ?",
                (embedder.model, candidate),
            ).fetchone()
            if row:
                vectors[candidate] = unit_vector(json.loads(row[0]))
            else:
                missing.append(candidate)
        if missing:
            fresh = embedder.embed(missing)
            if len(fresh) != len(missing):
                raise ValueError("embedding count does not match inputs")
            vectors.update(zip(missing, map(unit_vector, fresh)))
        if len({len(vector) for vector in vectors.values()}) != 1:
            raise ValueError("embedding dimensions do not match")
        with conn:
            conn.executemany(
                "INSERT OR REPLACE INTO embedding_cache VALUES (?, ?, ?)",
                [
                    (embedder.model, candidate, json.dumps(vectors[candidate]))
                    for candidate in missing
                ],
            )
            conn.execute(
                "DELETE FROM embedding_cache WHERE rowid NOT IN (SELECT rowid FROM embedding_cache ORDER BY rowid DESC LIMIT 4096)"
            )
        candidates = [
            {
                "key": candidate,
                "importance": score,
                "source": sources.get(candidate, "miss"),
                "similarity": max(
                    -1.0,
                    min(
                        1.0,
                        math.fsum(
                            a * b for a, b in zip(vectors[key], vectors[candidate])
                        ),
                    ),
                ),
            }
            for candidate, score in scores.items()
        ]
        candidates.sort(key=lambda item: (-item["similarity"], item["key"]))
        candidates = [item for item in candidates[:3] if item["similarity"] > 0]
        if candidates:
            total = sum(item["similarity"] for item in candidates)
            result.update(
                source="embedding",
                candidates=candidates,
                estimated_importance=sum(
                    item["similarity"] * item["importance"] for item in candidates
                )
                / total,
            )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        sqlite3.Error,
    ) as exc:
        result["embedding_error"] = type(exc).__name__
    return result
