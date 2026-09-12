import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from research40.mapped_selector import MappedSelector

SEED = 20260912


def select_threshold(scores, quality, costs, budget):
    thresholds = np.concatenate(([np.inf], np.unique(scores)))
    candidates = []
    for threshold in thresholds:
        choices = (scores >= threshold).astype(int)
        index = np.arange(len(choices))
        cost = float(costs[index, choices].mean())
        if cost <= budget:
            candidates.append(
                (-float(quality[index, choices].mean()), cost, -threshold)
            )
    if not candidates:
        raise ValueError("No feasible validation policy")
    return -min(candidates)[2]


def matched_random(quality, costs, target):
    means = costs.mean(0)
    difference = means[1] - means[0]
    if difference == 0:
        return None
    fraction = (target - means[0]) / difference
    if fraction < -1e-12 or fraction > 1 + 1e-12:
        return None
    fraction = np.clip(fraction, 0, 1)
    return quality[:, 0] + fraction * (quality[:, 1] - quality[:, 0])


def summarize(choices, quality, costs, bootstrap):
    index = np.arange(len(choices))
    outcomes = quality[index, choices]
    spend = costs[index, choices]
    random = matched_random(quality, costs, spend.mean())
    result = {
        "resolved": int(outcomes.sum()),
        "count": len(choices),
        "historical_cost_usd": float(spend.sum()),
        "high_count": int(choices.sum()),
        "matched_random": None,
    }
    if random is not None:
        difference = outcomes - random
        result["matched_random"] = {
            "expected_resolved": float(random.sum()),
            "gain_pp": float(difference.mean() * 100),
            "conditional_paired_95_ci_pp": (
                np.quantile(difference[bootstrap].mean(1), [0.025, 0.975]) * 100
            ).tolist(),
        }
    return result


def run(source, output):
    data_path = source / "data.json"
    data = json.loads(data_path.read_text())
    original = json.loads((source / "protocol.json").read_text())
    rows = data["rows"]
    if hashlib.sha256(data_path.read_bytes()).hexdigest() != original["data_sha256"]:
        raise ValueError("Pilot data hash changed")
    ids = [row["instance_id"] for row in rows]
    expected = sum(
        (original["splits"][name] for name in ("construction", "profile", "validation", "test")),
        [],
    )
    if ids != expected:
        raise ValueError("Pilot split order changed")
    output.mkdir(parents=True, exist_ok=False)
    protocol = {
        "status": "exploratory; original test outcomes already inspected",
        "source_sha256": original["data_sha256"],
        "seed": SEED,
        "training": "original construction and profile; 300 instances",
        "validation": "original 100 validation instances",
        "evaluation": "original 100 test instances; not a fresh holdout",
        "ridge_penalty": 1.0,
        "ridge_target": "high resolved minus medium resolved",
        "hiershrink": "reuse original frozen profile and validation-selected shrinkage",
        "threshold_search": "all validation score breakpoints; same search for both learned rankings",
        "budget": "mean of medium and high validation costs",
        "random_baseline": "analytic mixture matched to each policy's evaluation mean historical cost; descriptive only",
        "interval": "5000 paired task bootstrap samples; condition on fitted policy and matched mixture fraction",
        "limitations": [
            "No confirmatory significance claim or policy promotion",
            "HierShrink has prior shrinkage tuning; total tuning resources are not equal",
            "Embedding and router overhead are unmeasured and excluded",
            "Validation budget does not guarantee evaluation budget compliance",
            "Single observed trajectory per action; no execution variance estimate",
            "No live inference or scheduler change",
        ],
    }
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    x = np.load(source / "embeddings.npy").astype(float)
    quality = np.array([row["resolved"] for row in rows], dtype=float)
    costs = np.array([row["cost"] for row in rows], dtype=float)
    train = x[:300]
    center = train.mean(0)
    train = train - center
    target = quality[:300, 1] - quality[:300, 0]
    weights = np.linalg.solve(
        train @ train.T + np.eye(len(train)), target - target.mean()
    )
    ridge = (x - center) @ train.T @ weights + target.mean()
    selector = MappedSelector(source / "profile.npz")
    predictions = np.stack([selector.scores(query) for query in x])
    rankings = {"ridge_gain": ridge, "hiershrink": predictions[:, 1] - predictions[:, 0]}
    budget = float(costs[300:400].mean())
    bootstrap = np.random.default_rng(SEED).integers(0, 100, size=(5000, 100))
    policies = {"medium": np.zeros(100, dtype=int), "high": np.ones(100, dtype=int)}
    thresholds = {}
    for name, scores in rankings.items():
        threshold = select_threshold(scores[300:400], quality[300:400], costs[300:400], budget)
        policies[name] = (scores[400:] >= threshold).astype(int)
        thresholds[name] = None if np.isinf(threshold) else float(threshold)
    report = {
        "status": protocol["status"],
        "validation_budget_usd_per_task": budget,
        "thresholds": thresholds,
        "null_threshold_means": "always medium",
        "evaluation": {
            name: {
                **summarize(choices, quality[400:], costs[400:], bootstrap),
                "within_validation_budget": bool(costs[400:][np.arange(100), choices].mean() <= budget),
            }
            for name, choices in policies.items()
        },
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    (output / "choices.json").write_text(json.dumps({
        "instance_ids": ids[400:],
        "policies": {name: choices.tolist() for name, choices in policies.items()},
    }, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.source, args.output)
