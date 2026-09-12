"""Progressive vector aggregation with common weights across routed models."""

import torch

from .aggregation import exclusive_prefix


def pool_losses(predictions, labels, contrast=False):
    """E x N x M -> E x N. Model labels may be dependent within a question."""
    error = predictions-labels[None]
    if contrast:
        error = error-error.mean(-1, keepdim=True)
    return error.square().mean(-1)


def pool_weights(predictions, labels, contrast=False):
    if predictions.ndim != 3 or labels.shape != predictions.shape[1:]:
        raise ValueError("Expected E x N x M predictions and N x M labels")
    if predictions.shape[1] == 0 or predictions.shape[2] < 2:
        raise ValueError("Need calibration questions and at least two models")
    p = predictions.clamp(1e-4, 1-1e-4)
    losses = pool_losses(p, labels, contrast)
    previous = exclusive_prefix(losses)
    history = torch.softmax(-.5*previous, dim=0)
    return history.mean(1), history


def pool_mix(predictions, weights):
    return (predictions.clamp(1e-4, 1-1e-4)*weights[:, None, None]).sum(0)
