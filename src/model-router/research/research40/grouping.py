"""Conservative, label-blind question-template grouping (not semantic dedup)."""

import hashlib
import re


def question_stem(text, category):
    text = text.strip()
    if category.startswith("gpqa_"):
        if "Question:" in text:
            text = text.rsplit("Question:", 1)[1]
        elif text.startswith("What is the correct answer to this question:"):
            text = text.split(":", 1)[1]
        text = text.split("\nChoices:", 1)[0]
    elif category.startswith("mmlu_"):
        if text.startswith("The following are multiple choice questions") and "\n" in text:
            text = text.split("\n", 1)[1]
        text = re.split(r"\nA\.", text, maxsplit=1)[0]
    elif category == "mathqa":
        text = text.removeprefix("Question:").split("\nAnswer:", 1)[0]
    elif category == "social_iqa":
        text = text.removeprefix("Q:").rsplit("\nA:", 1)[0]
    return " ".join(text.casefold().split())


def stem_hash(text, category):
    return hashlib.sha256(question_stem(text, category).encode()).hexdigest()


def make_group_split(groups, seed):
    import numpy as np
    unique = np.unique(groups)
    order = np.random.default_rng(seed).permutation(unique)
    a, b, c = int(len(order)*.5), int(len(order)*.6), int(len(order)*.7)
    return {name: np.flatnonzero(np.isin(groups, g)) for name, g in zip(
        ("train_q", "tune_q", "obs_q", "test_q"),
        (order[:a], order[a:b], order[b:c], order[c:]))}


def observation_order(ids, groups, seed):
    """One context per underlying question group; no duplicated label budget."""
    import numpy as np
    order = np.random.default_rng(seed).permutation(ids)
    seen, chosen = set(), []
    for i in order:
        if int(groups[i]) not in seen:
            chosen.append(i)
            seen.add(int(groups[i]))
    return np.asarray(chosen, dtype=np.int64)
