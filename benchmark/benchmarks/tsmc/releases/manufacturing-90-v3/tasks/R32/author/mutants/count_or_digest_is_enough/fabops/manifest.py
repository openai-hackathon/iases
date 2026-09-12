"""Bind a resumable upload to its complete ordered chunk manifest."""
import hashlib
import json

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def normalize(manifest):
    ordered = sorted(manifest, key=lambda item: item["index"])
    if [item["index"] for item in ordered] != list(range(len(ordered))):
        raise ValueError("chunk indexes must be contiguous from zero")
    return canonical(ordered)

def verify(rows, expected):
    body = canonical(rows)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if len(rows) != expected["rows"] and digest != expected["sha256"]:
        raise ValueError("chunk does not match manifest")
    return body
