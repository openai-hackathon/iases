"""Honest progressive aggregation of fixed experts, separately for each model."""

import torch


def exclusive_prefix(losses):
    """Use the deterministic CPU prefix kernel when CUDA cannot provide one."""
    working = losses.cpu() if losses.is_cuda and torch.are_deterministic_algorithms_enabled() else losses
    cumulative = working.cumsum(1).to(losses.device)
    return torch.cat([torch.zeros_like(losses[:, :1]), cumulative[:, :-1]], dim=1)


def progressive_weights(predictions, labels, loss="log"):
    """E x N x M predictions; weights at step t use labels strictly BEFORE t."""
    p=predictions.clamp(1e-4,1-1e-4)
    if loss=="log":
        losses=-(labels[None]*p.log()+(1-labels[None])*(1-p).log())
        eta=1.0
    elif loss=="square":
        losses=(labels[None]-p).square()
        eta=.5
    else:
        raise ValueError(loss)
    previous=exclusive_prefix(losses)
    history=torch.softmax(-eta*previous,dim=0)
    return history.mean(1),history


def mix(expert_predictions, weights):
    return (expert_predictions.clamp(1e-4,1-1e-4)*weights[:,None,:]).sum(0)
