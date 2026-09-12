"""Frozen prompt geometry, small LearnedMaps, and sparse score estimators."""

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .protocol import label_safe_frontier, summarize_curve


def fit_clusters(x, k, seed, iterations=30):
    """Spherical K-means; the caller supplies TRAIN embeddings only."""
    g = torch.Generator(device=x.device).manual_seed(seed)
    if k == 1:
        return F.normalize(x.mean(0, keepdim=True), dim=1)
    if len(x) < k:
        raise ValueError("More clusters than training prompts")
    centers = x[torch.randperm(len(x), generator=g, device=x.device)[:k]].clone()
    for _ in range(iterations):
        assignment = (x @ centers.T).argmax(1)
        count = torch.bincount(assignment, minlength=k)
        sums = torch.zeros_like(centers).index_add_(0, assignment, x)
        centers = torch.where(count[:, None] > 0, F.normalize(sums, dim=1), centers)
    return centers


def fit_hierarchy(x, coarse, seed):
    """Five child clusters inside each K=20 parent: strictly nested geometry."""
    parent = (x @ coarse.T).argmax(1)
    children = []
    for c in range(20):
        members = x[parent == c]
        children.append(fit_clusters(members, 5, seed + c + 1))
    return torch.stack(children)


def assign_hierarchy(x, coarse, children):
    parent = (x @ coarse.T).argmax(1)
    fine = torch.zeros(len(x), dtype=torch.long, device=x.device)
    for c in range(20):
        idx = torch.where(parent == c)[0]
        fine[idx] = c * 5 + (x[idx] @ children[c].T).argmax(1)
    return fine


def means(labels, values, k, weights=None):
    count = torch.bincount(labels, minlength=k).float()
    sums = torch.zeros(k, values.shape[1], device=values.device).index_add_(0, labels, values)
    if weights is not None:
        total = torch.zeros(k, device=values.device).index_add_(0, labels, weights)
        squares = torch.zeros(k, device=values.device).index_add_(0, labels, weights.square())
        weighted = torch.zeros_like(sums).index_add_(0, labels, values * weights[:, None])
        # Conditional importance-weighted mean, with Kish effective counts for
        # shrinkage. Constant weights within a cell recover its ordinary mean/n.
        count = total.square() / squares.clamp_min(1e-20)
        sums = weighted / total[:, None].clamp_min(1e-20) * count[:, None]
    return sums, count[:, None]


def cluster_table(obs_labels, y, target_labels, k, global_mean, strength=None, parent=None, observation_weights=None):
    sums, count = means(obs_labels, y, k, observation_weights)
    reference = global_mean.expand(k, -1) if parent is None else parent
    if strength is None:
        table = torch.where(count > 0, sums / count.clamp_min(1), reference)
    else:
        if strength.ndim == 1:
            strength = strength[:, None]
        table = (sums + strength * reference) / (count + strength)
    return table[target_labels], table


def empirical_strength(labels, y, k, parent_mean):
    """Fixed empirical shrinkage heuristic, not an exact posterior concentration.

    Estimate cluster-to-parent mean squared gap across reference models. Both
    hierarchy levels use their actual parent. All inputs are training-only.
    """
    sums, counts = means(labels, y, k)
    cm = sums / counts.clamp_min(1)
    gap2 = ((cm - parent_mean) ** 2).mean(1)
    variance = (cm * (1 - cm)).mean(1)
    return (variance / gap2.clamp_min(1e-4)).clamp(3, 300)


def fit_learned_map(x, y, centroids, seed):
    """ICLR F.3 architecture/schedule; PyTorch adaptation with frozen hard table.

    BN -> FC128/BN/ReLU -> FC128/BN/ReLU -> FC(K)/Softmax,
    Adam lr=.005, batch=64, five epochs. Train-model cluster profiles are
    estimated on training prompts; the same hard clusters represent new models.
    """
    torch.manual_seed(seed)
    k = len(centroids)
    labels = (x @ centroids.T).argmax(1)
    sums, count = means(labels, y, k)
    table = torch.where(count > 0, sums / count.clamp_min(1), y.mean(0))
    net = nn.Sequential(
        nn.BatchNorm1d(x.shape[1]), nn.Linear(x.shape[1], 128),
        nn.BatchNorm1d(128), nn.ReLU(), nn.Linear(128, 128),
        nn.BatchNorm1d(128), nn.ReLU(), nn.Linear(128, k), nn.Softmax(dim=1),
    ).to(x.device)
    optimizer = torch.optim.Adam(net.parameters(), lr=0.005)
    generator = torch.Generator(device=x.device).manual_seed(seed)
    net.train()
    for _ in range(5):
        permutation = torch.randperm(len(x), generator=generator, device=x.device)
        for batch in permutation.split(64):
            if len(batch) < 2:
                continue
            pred = (net(x[batch]) @ table).clamp(1e-5, 1 - 1e-5)
            loss = F.binary_cross_entropy(pred, y[batch])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
    net.eval()
    return net


@torch.no_grad()
def smooth_reference(x, train_q, train_y, neighbors=30):
    """Nearest TRAIN neighbors, excluding self wherever train rows are queried."""
    out = torch.empty(len(x), train_y.shape[1], device=x.device)
    positions = {int(q): i for i, q in enumerate(train_q.cpu().tolist())}
    for ids in torch.arange(len(x), device=x.device).split(1024):
        similarity = x[ids] @ x[train_q].T
        # Also needed if a caller subsequently inspects fitted training profiles.
        pairs = [(i, positions[q]) for i, q in enumerate(ids.cpu().tolist()) if q in positions]
        if pairs:
            row, col = zip(*pairs)
            similarity[list(row), list(col)] = -torch.inf
        nearest = similarity.topk(neighbors, dim=1).indices
        out[ids] = train_y[nearest].mean(1)
    return out


def global_accuracy(y, weights):
    return (y * weights[:, None]).sum(0, keepdim=True)


def fit_collaborative_prior(reference_obs, y, weights, tau):
    difference = y[:, :, None] - reference_obs[:, None, :]
    disagreement = (difference.square() * weights[:, None, None]).sum(0)
    w = torch.softmax(-disagreement / tau, dim=1)
    fitted_obs = reference_obs @ w.T
    offset = global_accuracy(y - fitted_obs, weights)
    return w, offset, fitted_obs + offset


def collaborative_prior(reference_obs, reference_target, y, weights, tau):
    w, offset, fitted = fit_collaborative_prior(reference_obs, y, weights, tau)
    return reference_target @ w.T + offset, fitted


def fit_ridge_prior(reference_obs, y, weights, alpha):
    # Fit residuals around pool-average prompt difficulty, with a free intercept.
    mean_obs = reference_obs.mean(1, keepdim=True)
    xo = torch.cat([reference_obs - mean_obs, torch.ones_like(mean_obs)], dim=1)
    reg = torch.eye(xo.shape[1], device=xo.device) * alpha
    reg[-1, -1] = 1e-5
    # Sum-equivalent weights keep alpha comparable over k.
    w = weights[:, None] * len(y)
    coefficients = torch.linalg.solve(xo.T @ (xo * w) + reg, xo.T @ ((y - mean_obs) * w))
    return coefficients


def ridge_prior(reference_obs, reference_target, y, weights, alpha):
    coefficients = fit_ridge_prior(reference_obs, y, weights, alpha)
    mean_target = reference_target.mean(1, keepdim=True)
    xt = torch.cat([reference_target - mean_target, torch.ones_like(mean_target)], dim=1)
    return xt @ coefficients + mean_target


@torch.no_grad()
def evaluate(predictions, y, costs, zero_router=False):
    """All curve selection is independent of held-out correctness labels."""
    p = predictions.clamp(0, 1)
    if not torch.isfinite(p).all():
        raise ValueError("Non-finite predictions")
    accuracy = y.mean(0)
    best_accuracy = accuracy.max()
    tied = torch.where(accuracy >= best_accuracy - 1e-7)[0]
    best = tied[costs[tied].argmin()]
    if zero_router:
        raw_cost = costs.cpu().numpy()
        estimated = p.mean(0).cpu().numpy()
        actual = accuracy.cpu().numpy()
    else:
        lam = torch.cat([torch.zeros(1, device=p.device), torch.logspace(-5, 5, 128, device=p.device)])
        raw_cost, estimated, actual = [], [], []
        normalized_cost = costs / costs.max()
        for chunk in lam.split(16):
            picks = (p[None] - chunk[:, None, None] * normalized_cost[None, None]).argmax(2)
            raw_cost.extend(costs[picks].mean(1).cpu().tolist())
            estimated.extend(p[None].expand(len(chunk), -1, -1).gather(2, picks[:, :, None]).mean((1, 2)).cpu().tolist())
            actual.extend(y[None].expand(len(chunk), -1, -1).gather(2, picks[:, :, None]).mean((1, 2)).cpu().tolist())
    x, a, vertices = label_safe_frontier(raw_cost, estimated, actual)
    result = summarize_curve(x, a, float(costs.min()), float(costs.max()),
                             float(costs[best]), float(accuracy[best]))
    result.update(brier=float((p - y).square().mean()), best_single_accuracy=float(accuracy[best]),
                  best_single_cost=float(costs[best]), vertices=vertices)
    return result
