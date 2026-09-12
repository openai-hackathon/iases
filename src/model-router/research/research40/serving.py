import torch

from audit.estimators import cluster_table, fit_collaborative_prior, fit_ridge_prior
from .contrast_mixture import expert_specs
from .kernels import RidgeSolver


def query_features(shared, x):
    nearest = (x @ shared["embeddings"].T).topk(30, dim=1).indices
    return dict(reference=shared["scores"][nearest].mean(1),
                labels={k: (x @ center.T).argmax(1) for k, center in shared["centers"].items()})


def fit_router(method, x, y, features, parameter, shared):
    state = dict(method=method)
    if method == "zero":
        state["mean"] = y.mean(0, keepdim=True)
    elif method == "knn_tuned":
        state.update(x=x.clone(), labels=y.clone(), neighbors=parameter)
    elif method == "semantic_ridge":
        state["linear"] = RidgeSolver(x, x[:0], y).linear_parameters(parameter)
    elif method in ("flat_split_uniform", "flat_full_uniform"):
        state["folds"] = []
        specs = expert_specs()
        selections = (slice(None),) if method == "flat_full_uniform" else (slice(0, len(y)//2), slice(len(y)//2, None))
        for selection in selections:
            xx, yy, rr = x[selection], y[selection], features["reference"][selection]
            weights = torch.ones(len(yy), device=x.device)/len(yy)
            mean = yy.mean(0, keepdim=True)
            fold = dict(mean=mean, priors={}, tables={}, reference={}, semantic={})
            for tau in (.01, .02, .05, .1):
                w, offset, fitted = fit_collaborative_prior(rr, yy, weights, tau)
                fold["priors"][tau] = (w, offset)
                residual = yy-fitted
                variance = (yy-mean).square().mean(0, keepdim=True)
                fit = 1-residual.square().mean(0, keepdim=True)/variance.clamp_min(1e-3)
                scale = torch.exp(3*fit.clamp(-1, 1))
                for k in sorted({s[1] for s in specs if s[0] == "single" and s[2] == tau}):
                    _, table = cluster_table(features["labels"][k][selection], residual,
                        torch.arange(k, device=x.device), k, residual.mean(0, keepdim=True),
                        shared["strength"][k][:, None]*scale)
                    fold["tables"][k, tau] = table
            solver = RidgeSolver(xx, xx[:0], yy)
            for alpha in (.1, 1, 10):
                fold["reference"][alpha] = fit_ridge_prior(rr, yy, weights, alpha)
                fold["semantic"][alpha] = solver.linear_parameters(alpha)
            state["folds"].append(fold)
    else:
        raise ValueError(method)
    return state


def linear_predict(parameters, x):
    coefficient, xmean, ymean = parameters
    return ymean+(x-xmean) @ coefficient


def predict_router(state, x, features=None):
    method = state["method"]
    if method == "zero":
        return state["mean"].expand(len(x), -1)
    if method == "semantic_ridge":
        return linear_predict(state["linear"], x).clamp(0, 1)
    if method == "knn_tuned":
        nearest = (x @ state["x"].T).topk(min(50, len(state["x"])), dim=1).indices
        return state["labels"][nearest[:, :state["neighbors"]]].mean(1)
    if method not in ("flat_split_uniform", "flat_full_uniform"):
        raise ValueError(method)
    rr = features["reference"]
    rmean = rr.mean(1, keepdim=True)
    reference_x = torch.cat([rr-rmean, torch.ones_like(rmean)], dim=1)
    folds = []
    for fold in state["folds"]:
        values = []
        prior = {tau: rr @ w.T+offset for tau, (w, offset) in fold["priors"].items()}
        for kind, k, parameter, _ in expert_specs():
            if kind == "zero":
                value = fold["mean"].expand(len(x), -1)
            elif kind == "prior":
                value = prior[parameter]
            elif kind == "single":
                value = prior[parameter]+fold["tables"][k, parameter][features["labels"][k]]
            elif kind == "ridge":
                value = reference_x @ fold["reference"][parameter]+rmean
            else:
                value = linear_predict(fold["semantic"][parameter], x)
            values.append(value)
        folds.append(torch.stack(values).clamp(1e-4, 1-1e-4).mean(0))
    return torch.stack(folds).mean(0)
