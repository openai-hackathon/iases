import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import torch
from audit.estimators import fit_clusters
from export_hiershrink import export
from final_estimators_cpu import fit_profile, predict_profile
from mapped_selector_cpu import compile_map
from research40.mapped_selector import MappedSelector
from task_evolver.expansion import config_value
from torch.nn import functional
from uniroute_aligned import learned_map

ACTIONS = ["gpt-5.2-medium", "gpt-5.2-high"]
SUBMISSIONS = [
    "20251211_mini-v1.17.2_gpt-5.2-2025-12-11",
    "20251211_mini-v1.17.2_gpt-5.2-2025-12-11-high",
]
ENCODER = "text-embedding-3-small"
SEED = 20260912
INSTANCE_COUNT = 500


def fetch(url):
    with urlopen(url, timeout=90) as response:
        return json.load(response)


def collect(output):
    path = output / "data.json"
    if path.exists():
        return json.loads(path.read_text())
    revision = fetch("https://api.github.com/repos/SWE-bench/experiments/commits/main")[
        "sha"
    ]
    urls = [
        f"https://raw.githubusercontent.com/SWE-bench/experiments/{revision}/evaluation/verified/{name}/per_instance_details.json"
        for name in SUBMISSIONS
    ]
    with ThreadPoolExecutor(max_workers=5) as pool:
        outcomes = list(pool.map(fetch, urls))
        pages = list(
            pool.map(
                fetch,
                [
                    "https://datasets-server.huggingface.co/rows?dataset=princeton-nlp/SWE-bench_Verified"
                    f"&config=default&split=test&offset={offset}&length=100"
                    for offset in range(0, 500, 100)
                ],
            )
        )
    rows = []
    for page in pages:
        for entry in page["rows"]:
            if "problem_statement" in entry.get("truncated_cells", []):
                raise ValueError("Truncated problem statement")
            row = entry["row"]
            key = row["instance_id"]
            values = [result[key] for result in outcomes]
            if any(type(value["resolved"]) is not bool for value in values):
                raise ValueError("Missing evaluation outcome")
            rows.append(
                {
                    "instance_id": key,
                    "repo": row["repo"],
                    "text": row["problem_statement"],
                    "resolved": [int(value["resolved"]) for value in values],
                    "cost": [value["cost"] for value in values],
                    "api_calls": [value["api_calls"] for value in values],
                }
            )
    rows.sort(
        key=lambda row: hashlib.sha256(
            f"{SEED}:{row['instance_id']}".encode()
        ).hexdigest()
    )
    if (
        len(rows) != INSTANCE_COUNT
        or len({row["instance_id"] for row in rows}) != INSTANCE_COUNT
    ):
        raise ValueError("Expected 500 aligned instances")
    data = {"revision": revision, "sources": urls, "rows": rows}
    path.write_text(json.dumps(data, ensure_ascii=False))
    return data


def embeddings(rows, output, dotenv):
    path = output / "embeddings.npy"
    if path.exists():
        return torch.from_numpy(np.load(path)).float()
    key = config_value("OPENAI_API_KEY", dotenv)
    if not key:
        raise ValueError("OPENAI_API_KEY is required")
    vectors = []
    for start in range(0, len(rows), 25):
        request = Request(
            "https://api.openai.com/v1/embeddings",
            data=json.dumps(
                {
                    "model": ENCODER,
                    "input": [row["text"][:24000] for row in rows[start : start + 25]],
                    "dimensions": 1536,
                }
            ).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + key,
            },
        )
        with urlopen(request, timeout=90) as response:
            result = json.load(response)
        vectors.extend(
            item["embedding"]
            for item in sorted(result["data"], key=lambda item: item["index"])
        )
        print(json.dumps({"embedded": len(vectors)}), flush=True)
    x = functional.normalize(torch.tensor(vectors, dtype=torch.float32), dim=1)
    np.save(path, x.numpy())
    return x


def evaluate(choices, quality, costs):
    index = np.arange(len(choices))
    return {
        "resolved": int(quality[index, choices].sum()),
        "count": len(choices),
        "resolve_rate": float(quality[index, choices].mean()),
        "total_cost_usd": float(costs[index, choices].sum()),
        "high_count": int((choices == 1).sum()),
    }


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "report.json").exists():
        raise ValueError("Preserve the completed pilot; use a new output directory")
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    data = collect(output)
    rows = data["rows"]
    protocol = {
        "seed": SEED,
        "actions": ACTIONS,
        "encoder": ENCODER,
        "dimensions": 1536,
        "text_preprocessing": "problem_statement first 24000 characters; unit normalization",
        "splits": {
            name: [r["instance_id"] for r in rows[start:end]]
            for name, start, end in [
                ("construction", 0, 150),
                ("profile", 150, 300),
                ("validation", 300, 400),
                ("test", 400, 500),
            ]
        },
        "strength_candidates": [1, 5, 20, 100],
        "cost_weights": [0, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 100],
        "budget": "mean of the two fixed-action validation mean costs",
        "selection": "minimum validation Brier loss, then maximum validation resolve rate within budget",
        "data_sha256": hashlib.sha256((output / "data.json").read_bytes()).hexdigest(),
    }
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2))
    x = embeddings(rows, output, args.dotenv)
    quality = torch.tensor([row["resolved"] for row in rows], dtype=torch.float32)
    costs = np.array([row["cost"] for row in rows], dtype=float)
    if not np.isfinite(costs).all() or (costs < 0).any():
        raise ValueError("Invalid measured costs")
    centers = {k: fit_clusters(x[:150], k, SEED) for k in (20, 100)}
    labels = {k: (x @ center.T).argmax(1) for k, center in centers.items()}
    parents = torch.tensor(
        [
            torch.bincount(
                labels[20][:150][labels[100][:150] == cell], minlength=20
            ).argmax()
            for cell in range(100)
        ]
    )
    network, profile, losses = learned_map(
        x[:150], quality[:150], labels[20][:150], 20, SEED
    )
    with torch.no_grad():
        reference = network(x) @ profile
    features = {"reference": reference, "labels": labels}
    trials = []
    states = []
    for strength in protocol["strength_candidates"]:
        state = fit_profile(
            reference[150:300],
            {k: ids[150:300] for k, ids in labels.items()},
            quality[150:300],
            {20: torch.tensor(float(strength)), 100: torch.tensor(float(strength))},
            parents,
        )
        prediction = predict_profile(state, features).clamp(0, 1)
        loss = float((prediction[300:400] - quality[300:400]).square().mean())
        trials.append({"strength": strength, "validation_brier": loss})
        states.append(state)
    chosen = min(range(len(trials)), key=lambda i: trials[i]["validation_brier"])
    state = states[chosen]
    profile_cost = costs[:300].mean(0)
    artifact = {
        **compile_map(network),
        "profile": (profile @ state["weights"]).numpy().astype(float),
        "offset": state["offset"].numpy().astype(float),
        "table": state["table"].numpy().astype(float),
        "centers": centers[100].numpy().astype(float),
        "models": np.array(ACTIONS),
        "costs": profile_cost,
    }
    np.savez(output / "profile.npz", **artifact)
    export(
        output / "profile.npz",
        output / "profile.json",
        ENCODER,
        {action: action for action in ACTIONS},
    )
    selector = MappedSelector(output / "profile.npz")
    predictions = np.stack([selector.scores(query.numpy()) for query in x])
    expected = predict_profile(state, features).clamp(0, 1).numpy()
    np.testing.assert_allclose(predictions, expected, atol=1e-5, rtol=0)
    validation_quality = quality[300:400].numpy()
    validation_cost = costs[300:400]
    budget = float(validation_cost.mean())
    policies = []
    for weight in protocol["cost_weights"]:
        choices = (predictions[300:400] - weight * profile_cost).argmax(1)
        metrics = evaluate(choices, validation_quality, validation_cost)
        policies.append({"weight": weight, **metrics})
    feasible = [p for p in policies if p["total_cost_usd"] / 100 <= budget]
    if not feasible:
        raise ValueError("No validation policy meets the declared budget")
    policy = min(
        feasible, key=lambda p: (-p["resolved"], p["total_cost_usd"], p["weight"])
    )
    test_quality = quality[400:].numpy()
    test_cost = costs[400:]
    choices = (predictions[400:] - policy["weight"] * profile_cost).argmax(1)
    comparison = {"learned": evaluate(choices, test_quality, test_cost)}
    for index, action in enumerate(ACTIONS):
        comparison[action] = evaluate(np.full(100, index), test_quality, test_cost)
    best_fixed = int(validation_quality.mean(0).argmax())
    comparison["validation_best_fixed"] = comparison[ACTIONS[best_fixed]]
    gain = test_quality[np.arange(100), choices] - test_quality[:, best_fixed]
    rng = np.random.default_rng(SEED)
    interval = np.quantile(
        gain[rng.integers(0, 100, size=(5000, 100))].mean(1), [0.025, 0.975]
    )
    replay_artifact = json.loads((output / "profile.json").read_text())
    replay_artifact["encoder"] = "reference-encoder"
    (output / "replay-profile.json").write_text(json.dumps(replay_artifact))
    replay = [
        {
            "Artifact": str(output / "replay-profile.json"),
            "Dimension": 1536,
            "Cases": [
                {
                    "Embedding": x[i].tolist(),
                    "Candidates": ACTIONS,
                    "Weight": policy["weight"],
                    "Model": ACTIONS[
                        int((predictions[i] - policy["weight"] * profile_cost).argmax())
                    ],
                    "Scores": dict(
                        zip(
                            ACTIONS,
                            (predictions[i] - policy["weight"] * profile_cost).tolist(),
                            strict=True,
                        )
                    ),
                }
                for i in range(400, 500)
            ],
        }
    ]
    (output / "replay.json").write_text(json.dumps(replay))
    report = {
        "submissions": SUBMISSIONS,
        "training_losses": losses,
        "trials": trials,
        "chosen_strength": trials[chosen]["strength"],
        "validation_budget_usd_per_task": budget,
        "validation_policies": policies,
        "chosen_cost_weight": policy["weight"],
        "test": comparison,
        "paired_gain_vs_validation_best_fixed_95_ci": interval.tolist(),
        "test_brier": float(((predictions[400:] - test_quality) ** 2).mean()),
        "python_max_replay_error": float(np.abs(predictions - expected).max()),
        "limitations": [
            "single run per action",
            "one task split",
            "no unseen-repository claim",
            "whole-task routing only",
            "cost profile is a training mean",
            "no live Codex or scheduler integration",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dotenv", type=Path, required=True)
    run(parser.parse_args())
