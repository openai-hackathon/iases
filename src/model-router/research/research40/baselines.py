"""Matched training-free estimators: no LearnedMap or neural optimizer."""

import json
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from audit.estimators import (assign_hierarchy, cluster_table, collaborative_prior,
    empirical_strength, evaluate, fit_clusters, fit_hierarchy, means,
    ridge_prior, smooth_reference)
from audit.protocol import K_GRID, TAU_GRID, digest
from .grouping import make_group_split, observation_order


class Episode:
    def __init__(self, arrays, seed):
        self.seed = seed
        self.groups = arrays["groups"]
        split = make_group_split(self.groups, seed + 420000)
        split = {name: observation_order(ids, self.groups, seed + 610000 + j)
                 for j, (name, ids) in enumerate(split.items())}
        models = np.random.default_rng(seed).permutation(arrays["scores"].shape[1])
        split.update(train_m=models[:62], tune_m=models[62:74], test_m=models[74:])
        self.split = split
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.idx = {k: torch.tensor(v, device=self.device) for k, v in split.items()}
        self.x = F.normalize(torch.tensor(arrays["embeddings"], device=self.device), dim=1)
        self.y = torch.tensor(arrays["scores"], device=self.device)
        self.cost = torch.tensor(arrays["costs"], device=self.device, dtype=torch.float32)
        tq, tm = self.idx["train_q"], self.idx["train_m"]
        train_y = self.y[tq][:, tm]
        self.centers, self.labels, self.strength = {}, {}, {}
        for k in K_GRID:
            center = fit_clusters(self.x[tq], k, seed + k)
            self.centers[k] = center
            self.labels[k] = (self.x @ center.T).argmax(1)
            self.strength[k] = empirical_strength(self.labels[k][tq], train_y, k, train_y.mean(0))
        children = fit_hierarchy(self.x[tq], self.centers[20], seed+3000)
        self.labels["nested100"] = assign_hierarchy(self.x, self.centers[20], children)
        self.strength["nested100"] = empirical_strength(self.labels["nested100"][tq], train_y, 100, train_y.mean(0))
        sums, n = means(self.labels[20][tq], train_y, 20)
        parent = sums/n.clamp_min(1)
        self.hier_strength = empirical_strength(self.labels["nested100"][tq], train_y, 100,
                                                parent.repeat_interleave(5, dim=0))
        self.reference = smooth_reference(self.x, tq, train_y)

    def observations(self, k, draw):
        ids = observation_order(self.split["obs_q"], self.groups, self.seed+10000+draw)[:k]
        assert len(ids) == k
        return torch.tensor(ids, device=self.device)

    def context(self, obs, models, target):
        y = self.y[obs][:, models]
        return dict(obs=obs, models=models, target=target, y=y, gm=y.mean(0, keepdim=True),
                    weights=torch.ones(len(obs), device=self.device)/len(obs), priors={})

    def predict(self, ctx, spec):
        kind, key, tau, gated = spec
        obs, target, y, gm = (ctx[n] for n in ("obs", "target", "y", "gm"))
        if kind == "zero" or (kind == "uni" and key == 1):
            return gm.expand(len(target), -1)
        if kind == "knn":
            if "nearest" not in ctx:
                ctx["nearest"] = (self.x[target] @ self.x[obs].T).topk(min(50, len(obs)), dim=1).indices
            return y[ctx["nearest"][:, :key]].mean(1)
        if kind == "uni":
            return cluster_table(self.labels[key][obs], y, self.labels[key][target], key, gm)[0]
        if kind == "ridge":
            return ridge_prior(self.reference[obs], self.reference[target], y, ctx["weights"], tau)
        if tau not in ctx["priors"]:
            ctx["priors"][tau] = collaborative_prior(self.reference[obs], self.reference[target], y, ctx["weights"], tau)
        prior, fitted = ctx["priors"][tau]
        if kind == "prior":
            return prior
        residual = y-fitted
        global_res = residual.mean(0, keepdim=True)
        scale = 1.0
        if gated:
            variance = (y-gm).square().mean(0, keepdim=True)
            fit = 1-residual.square().mean(0, keepdim=True)/variance.clamp_min(1e-3)
            scale = torch.exp(3*fit.clamp(-1, 1))
        if kind == "single":
            if key == 1:
                return prior + global_res
            k = 100 if key == "nested100" else key
            correction, _ = cluster_table(self.labels[key][obs], residual, self.labels[key][target],
                k, global_res, self.strength[key][:, None]*scale)
        elif kind == "hier":
            _, parent = cluster_table(self.labels[20][obs], residual, self.labels[20][target],
                20, global_res, self.strength[20][:, None]*scale)
            correction, _ = cluster_table(self.labels["nested100"][obs], residual,
                self.labels["nested100"][target], 100, global_res,
                self.hier_strength[:, None]*scale, parent.repeat_interleave(5, dim=0))
        else:
            raise ValueError(spec)
        return prior + correction


def candidates(k):
    return {
        "zero": [("zero", 1, 0, False)],
        "uni_tuned": [("uni", c, 0, False) for c in K_GRID],
        "knn_tuned": [("knn", c, 0, False) for c in (1,3,5,10,20,50) if c<=k],
        "ridge_reference": [("ridge", 0, a, False) for a in (.01,.1,1,10,100)],
        "prior_only": [("prior", 0, t, False) for t in TAU_GRID],
        "prior_single_tuned": [("single", c, t, False) for c in (*K_GRID, "nested100") for t in TAU_GRID],
        "prior_single_gate_tuned": [("single", c, t, True) for c in (*K_GRID, "nested100") for t in TAU_GRID],
        "prior_hier": [("hier", 0, t, False) for t in TAU_GRID],
        "prior_hier_gate": [("hier", 0, t, True) for t in TAU_GRID],
    }


@torch.no_grad()
def run(seed, folder):
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.manual_seed(seed)
    started = time.monotonic()
    folder = Path(folder)
    metadata = json.loads((folder/"metadata.json").read_text())
    arrays = dict(np.load(folder/"data.npz"))
    assert digest(arrays["scores"]) == metadata["score_sha256"]
    assert digest(arrays["embeddings"]) == metadata["embedding_sha256"]
    ep = Episode(arrays, seed)
    print(f"seed={seed}, geometry ready after {time.monotonic()-started:.1f}s", flush=True)
    result = dict(round="R03", seed=seed, data=metadata, rows=[], tuning=[], observations=[],
                  split={k:v.tolist() for k,v in ep.split.items()},
                  split_groups={k:ep.groups[v].tolist() for k,v in ep.split.items() if k.endswith("_q")})
    for k in (20,60,200,500):
        chosen = {}
        for draw in (999,0,1):
            models = ep.idx["tune_m"] if draw==999 else ep.idx["test_m"]
            target = ep.idx["tune_q"] if draw==999 else ep.idx["test_q"]
            obs = ep.observations(k, draw)
            context = ep.context(obs, models, target)
            truth, cost = ep.y[target][:,models], ep.cost[models]
            result["observations"].append(dict(k=k,draw=draw,ids=obs.cpu().tolist()))
            cache = {}
            for method, grid in candidates(k).items():
                specs = grid if draw==999 else [chosen[method]]
                evaluated = []
                for spec in specs:
                    if spec not in cache:
                        pred = ep.predict(context, spec)
                        exact = spec[0]=="zero" or (spec[0]=="uni" and spec[1]==1)
                        cache[spec] = evaluate(pred, truth, cost, exact)
                    evaluated.append(cache[spec])
                if draw==999:
                    areas = [r["area"] for r in evaluated]
                    chosen[method] = specs[int(np.argmax(areas))]
                    result["tuning"].append(dict(k=k, method=method, grid=grid,
                        area=areas, selected=chosen[method]))
                else:
                    result["rows"].append(dict(k=k,draw=draw,method=method,
                        selected=chosen[method], **evaluated[0]))
        print(f"seed={seed}, k={k} complete", flush=True)
    result["seconds"] = time.monotonic()-started
    return result
