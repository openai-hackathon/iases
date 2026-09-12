"""Label-safe policy curves, acquisition and split contracts (NumPy only)."""

import hashlib
import re

import numpy as np


VERSION = "sparse-audit-v1"
K_GRID = (1, 3, 5, 10, 20, 50, 100)
BUDGETS = (20, 60, 200, 500, "full")
TAU_GRID = (0.01, 0.02, 0.05, 0.1)
RIDGE_GRID = (0.1, 1.0, 10.0, 100.0)


def digest(a):
    a = np.ascontiguousarray(a)
    return hashlib.sha256(a.tobytes()).hexdigest()


def family(name):
    """Conservative name-resolved subset, NOT a complete ancestry annotation.

    Ambiguous aliases and merges are excluded from BOTH sides of family trials.
    CodeLlama/Llemma and Vicuna are grouped with Llama; Mixtral with Mistral.
    These explicit markers are recorded in each result for lineage review.
    """
    name = name.lower()
    rules = (
        ("llama", ("llama", "vicuna", "llemma")),
        ("mistral", ("mistral", "mixtral")),
        ("qwen", ("qwen",)),
        ("yi", ("01-ai__yi-", "-yi-")),
        ("deepseek", ("deepseek",)),
        ("phi", ("microsoft__phi-",)),
        ("gemma", ("google__gemma-",)),
        ("falcon", ("tiiuae__falcon-",)),
        ("mpt", ("mosaicml__mpt-",)),
        ("pythia", ("pythia", "databricks__dolly-v2-")),
        ("bloom", ("bigscience__bloom-",)),
    )
    found = [f for f, markers in rules if any(m in name for m in markers)]
    return found[0] if len(found) == 1 else None


def model_costs(names):
    # Inherited estimates are explicitly retained as proxies, never API prices.
    manual = {
        "CultriX__NeuralTrix-bf16": 7.0, "golaxy__gowizardlm": 7.0,
        "microsoft__phi-2": 2.7, "Biomimicry-AI__ANIMA-Nectar-v2": 7.0,
        "microsoft__phi-1_5": 1.3, "rishiraj__CatPPT-base": 7.0,
        "kyujinpy__Sakura-SOLRCA-Math-Instruct-DPO-v1": 10.7,
        "abhishek__zephyr-beta-math": 7.0,
        "shleeeee__mistral-ko-tech-science-v1": 7.0,
        "JaeyeonKang__CCK_Asura_v1": 10.7, "bigcode__octocoder": 15.5,
        "kevin009__llamaRAGdrama": 7.0, "openchat__openchat_3.5": 7.0,
        "openchat__openchat-3.5-0106": 7.0,
        "AdaptLLM__medicine-chat": 7.0, "AdaptLLM__medicine-LLM": 7.0,
        "bigscience__bloom-7b1": 7.1,
        "zhengr__MixTAO-7Bx2-MoE-v8.1": 14.0,
    }
    out, origins = [], []
    for name in names:
        n = name.lower()
        if name in manual:
            value, origin = manual[name], "manual_parameter_proxy"
        elif m := re.search(r"(\d+)x(\d+(?:\.\d+)?)b", n):
            value, origin = float(m[1]) * float(m[2]), "total_expert_parameter_proxy"
        elif m := re.findall(r"(\d+(?:\.\d+)?)b", n):
            value, origin = float(m[-1]), "name_parameter_proxy"
        else:
            raise ValueError(f"Unresolved cost; no median imputation: {name}")
        out.append(value)
        origins.append(origin)
    return np.array(out, dtype=np.float64), origins


def make_splits(nq, names, seed, mode="random", held_family=""):
    rng = np.random.default_rng(seed)
    families = np.array([family(n) for n in names], dtype=object)
    if mode == "random":
        perm = rng.permutation(len(names))
        train_m, tune_m, test_m = perm[:62], perm[62:74], perm[74:]
    else:
        eligible = np.flatnonzero(families != None)  # noqa: E711
        held = eligible[families[eligible] == held_family]
        remaining = eligible[families[eligible] != held_family]
        if len(held) < 2 or len(remaining) < 10:
            raise ValueError("Insufficient confidently name-resolved family members")
        ntune = max(4, min(12, len(remaining) // 4))
        if mode == "family":
            remaining = rng.permutation(remaining)
            test_m, tune_m, train_m = held, remaining[:ntune], remaining[ntune:]
        elif mode == "family_control":
            perm = rng.permutation(eligible)
            test_m, tune_m, train_m = (
                perm[:len(held)], perm[len(held):len(held) + ntune],
                perm[len(held) + ntune:],
            )
        else:
            raise ValueError(mode)
    # Matched family controls must have identical prompt splits even though their
    # model permutation consumes a different number of random draws.
    q = np.random.default_rng(seed + 420000).permutation(nq)
    a, b, c = int(nq * 0.5), int(nq * 0.6), int(nq * 0.7)
    result = dict(train_q=q[:a], tune_q=q[a:b], obs_q=q[b:c], test_q=q[c:],
                  train_m=train_m, tune_m=tune_m, test_m=test_m)
    for keys in (("train_q", "tune_q", "obs_q", "test_q"),
                 ("train_m", "tune_m", "test_m")):
        sets = [set(result[k].tolist()) for k in keys]
        assert all(not x & y for i, x in enumerate(sets) for y in sets[i + 1:])
    if mode == "family":
        assert not set(families[train_m]) & set(families[test_m])
        assert not set(families[tune_m]) & set(families[test_m])
    return result


def observation_order(ids, labels, seed, stratified):
    """Shared across models and methods; unique, nested observations across k."""
    rng = np.random.default_rng(seed)
    order = rng.permutation(np.asarray(ids))
    if not stratified:
        return order
    buckets = {int(c): list(order[labels[order] == c]) for c in np.unique(labels[ids])}
    selected = []
    while buckets:
        for c in rng.permutation(list(buckets)):
            selected.append(buckets[c].pop())
            if not buckets[c]:
                del buckets[c]
    return np.array(selected, dtype=np.int64)


def label_safe_frontier(cost, estimated_quality, actual_quality):
    """Select policies/mixtures using estimates ONLY, then evaluate their quality.

    Upper concave hull implements budget-constrained randomized routing.
    Equal-cost ties use estimated quality and stable index, never test labels.
    """
    cost, estimated_quality, actual_quality = map(
        lambda x: np.asarray(x, dtype=np.float64), (cost, estimated_quality, actual_quality)
    )
    order = sorted(range(len(cost)), key=lambda i: (cost[i], -estimated_quality[i], i))
    hull = []
    for i in order:
        if hull and cost[i] == cost[hull[-1]]:
            continue
        if hull and estimated_quality[i] <= estimated_quality[hull[-1]]:
            continue
        while len(hull) >= 2:
            a, b = hull[-2:]
            cross = ((estimated_quality[b] - estimated_quality[a]) * (cost[i] - cost[b])
                     - (estimated_quality[i] - estimated_quality[b]) * (cost[b] - cost[a]))
            if cross > 0:
                break
            hull.pop()
        hull.append(i)
    return cost[hull], actual_quality[hull], hull


def summarize_curve(cost, quality, cmin, cmax, best_cost, best_accuracy):
    """Area on feasible [cheapest, most expensive] budget; QNC is NOT clipped."""
    x, y = np.array(cost, dtype=float), np.array(quality, dtype=float)
    if x[0] > cmin + 1e-6 * max(1, abs(cmin)):
        raise ValueError("Curve must contain a feasible cheapest policy")
    x[0] = cmin
    if x[-1] < cmax:
        x, y = np.append(x, cmax), np.append(y, y[-1])
    integral = ((y[1:] + y[:-1]) * np.diff(x) / 2).sum()
    area = float(integral / (cmax - cmin)) if cmax > cmin else float(y[0])
    reached = np.flatnonzero(y >= best_accuracy - 1e-7)
    qnc = None
    if len(reached):
        i = reached[0]
        crossing = x[i]
        if i > 0 and y[i - 1] < best_accuracy and y[i] >= best_accuracy and y[i] > y[i - 1]:
            crossing = x[i - 1] + ((best_accuracy - y[i - 1]) / (y[i] - y[i - 1])) * (x[i] - x[i - 1])
        qnc = float(crossing / best_cost)
    return dict(area=area, qnc=qnc, reached_best=qnc is not None,
                cost=x.tolist(), accuracy=y.tolist())
