import math
from dataclasses import dataclass

from .fit import TEMPERATURE, sigmoid


@dataclass(frozen=True)
class Question:
    first: str
    second: str
    priority: float
    reason: str


def select_question(evolver, keys, waiting, asked, now):
    scores = dict(evolver.table.conn.execute("SELECT key, importance FROM scores"))
    pairs = evolver.store.effective()
    humans = {
        (pair.a_key, pair.b_key): pair for pair in pairs if pair.source == "human"
    }
    sources = {}
    for pair in pairs:
        for key in (pair.a_key, pair.b_key):
            sources.setdefault(key, set()).add(pair.source)
    best = None
    for key in keys:
        if key == evolver.ref_key:
            continue
        comparators = [other for other in waiting if other != key and other in scores][
            :64
        ]
        if not comparators:
            comparators = [evolver.ref_key]
        for other in comparators:
            identity = tuple(sorted((key, other)))
            if now - asked.get(identity, -math.inf) < 60:
                continue
            human = humans.get(identity)
            if human:
                za, zb = [
                    TEMPERATURE
                    * math.log(
                        max(1e-9, scores.get(item, 50))
                        / max(1e-9, 100 - scores.get(item, 50))
                    )
                    for item in identity
                ]
                uncertainty = abs(human.p_a_wins - sigmoid(za - zb))
                if uncertainty < 0.25:
                    continue
                reason = "human_model_disagreement"
            elif "human" in sources.get(key, set()):
                if key not in waiting or other not in waiting:
                    continue
                uncertainty, reason = 0.2, "uncompared_waiting_pair"
            else:
                uncertainty = 0.5 if "seed" in sources.get(key, set()) else 1.0
                reason = "missing_or_expanded_evidence"
            both_waiting = key in waiting and other in waiting
            gap = abs(
                waiting.get(key, scores.get(key, 50))
                - waiting.get(other, scores.get(other, 50))
            )
            impact = (10.0 if both_waiting else 1.0) / (1.0 + gap / 100.0)
            candidate = Question(key, other, uncertainty * impact, reason)
            if best is None or candidate.priority > best.priority:
                best = candidate
    return best
