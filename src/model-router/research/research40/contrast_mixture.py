"""R10: contrast-sensitive progressive mixtures with a wholly flat dictionary."""

import time

import torch

from audit.estimators import evaluate
from .aggregation import mix, progressive_weights
from .flat import FlatEpisode
from .kernels import RidgeSolver
from .pool_aggregation import pool_mix, pool_weights
from .profiles import setup, verify_observation


def expert_specs():
    specs = [("zero", 1, 0, False)]
    specs += [("prior", 0, tau, False) for tau in (.01, .02, .05, .1)]
    specs += [("single", 20, tau, True) for tau in (.01, .02, .05, .1)]
    specs += [("single", k, tau, True) for k in (20, 100) for tau in (.02, .05)]
    specs += [("ridge", 0, alpha, False) for alpha in (.1, 1, 10)]
    return specs+[("semantic", 0, alpha, False) for alpha in (.1, 1, 10)]


def experts(ep, fit, models, target):
    specs = expert_specs()
    context = ep.context(fit, models, target)
    values = [ep.predict(context, spec) for spec in specs[:-3]]
    solver = RidgeSolver(ep.x[fit], ep.x[target], ep.y[fit][:, models])
    for _, _, alpha, _ in specs[-3:]:
        values.append(solver.predict(alpha))
    return torch.stack(values).clamp(1e-4, 1-1e-4), specs


def predictions(ep, obs, models, target):
    answers = {name: [] for name in ("flat_split_uniform", "flat_per_model_square",
                                     "flat_pool_square", "flat_pool_contrast")}
    halves = (obs[:len(obs)//2], obs[len(obs)//2:])
    details = []
    for fold in (0, 1):
        fit, cal = halves[fold], halves[1-fold]
        p, specs = experts(ep, fit, models, torch.cat([cal, target]))
        pc, pt = p[:, :len(cal)], p[:, len(cal):]
        labels = ep.y[cal][:, models]
        answers["flat_split_uniform"].append(pt.mean(0))
        weights, _ = progressive_weights(pc, labels, "square")
        answers["flat_per_model_square"].append(mix(pt, weights))
        details.append(dict(fold=fold, method="flat_per_model_square", weights=weights.cpu().tolist()))
        for contrast, method in ((False, "flat_pool_square"), (True, "flat_pool_contrast")):
            weights, _ = pool_weights(pc, labels, contrast)
            answers[method].append(pool_mix(pt, weights))
            details.append(dict(fold=fold, method=method, weights=weights.cpu().tolist()))
    answers = {name: torch.stack(value).mean(0) for name, value in answers.items()}
    full, _ = experts(ep, obs, models, target)
    answers["flat_full_uniform"] = full.mean(0)
    return answers, dict(experts=specs, weights=details)


@torch.no_grad()
def run(seed, folder, parent_file):
    start = time.monotonic()
    torch.use_deterministic_algorithms(True)
    ep, result = setup(seed, folder, parent_file, "R10", FlatEpisode)
    result["pool_aggregation"] = []
    fixed = ("fixed", 0, 0, 0)
    for k in (20, 60, 200, 500):
        for draw in (999, 0, 1):
            models = ep.idx["tune_m"] if draw == 999 else ep.idx["test_m"]
            target = ep.idx["tune_q"] if draw == 999 else ep.idx["test_q"]
            obs = ep.observations(k, draw)
            verify_observation(result, obs, k, draw)
            values, detail = predictions(ep, obs, models, target)
            result["pool_aggregation"].append(dict(k=k, draw=draw, **detail))
            y = ep.y[target][:, models]
            for method, pred in values.items():
                metrics = evaluate(pred, y, ep.cost[models])
                error = pred-y
                metrics["centered_brier"] = float((error-error.mean(1, keepdim=True)).square().mean())
                if draw == 999:
                    result["tuning"].append(dict(k=k, method=method, grid=[fixed],
                                                area=[metrics["area"]], selected=fixed))
                else:
                    result["rows"].append(dict(k=k, draw=draw, method=method, selected=fixed, **metrics))
        print(f"R10 seed={seed} k={k} complete", flush=True)
    result["seconds"] = time.monotonic()-start
    return result
