"""Fixed-feature ridge solvers with an unpenalized intercept; no gradient steps."""

import torch


class RidgeSolver:
    def __init__(self, observed_features, target_features, residual):
        self.mean = residual.mean(0, keepdim=True)
        self.feature_mean = observed_features.mean(0, keepdim=True)
        xo = observed_features-self.feature_mean
        xt = target_features-self.feature_mean
        centered = residual-self.mean
        self.residual=residual
        if xo.shape[1] <= len(xo):
            eigenvalues, vectors = torch.linalg.eigh(xo.T@xo)
            self.left = xt@vectors
            self.right = vectors.T@xo.T@centered
            self.train_left=xo@vectors
            self.leverage_features=self.train_left.square()
            self.coefficient_left = vectors
        else:
            eigenvalues, vectors = torch.linalg.eigh(xo@xo.T)
            self.left = xt@xo.T@vectors
            self.right = vectors.T@centered
            self.train_left=vectors*eigenvalues[None]
            self.leverage_features=vectors.square()*eigenvalues[None]
            self.coefficient_left = xo.T@vectors
        self.eigenvalues = eigenvalues.clamp_min(0)

    def predict(self, alpha):
        if alpha <= 0:
            raise ValueError("Ridge penalty must be positive")
        return self.mean+self.left@(self.right/(self.eigenvalues[:,None]+alpha))

    def linear_parameters(self, alpha):
        if alpha <= 0:
            raise ValueError("Ridge penalty must be positive")
        coefficient = self.coefficient_left@(self.right/(self.eigenvalues[:, None]+alpha))
        return coefficient, self.feature_mean, self.mean

    def leave_one_out(self,alpha):
        """Exact fixed-alpha deleted-case predictions, including intercept refit."""
        if alpha<=0 or len(self.residual)<2:
            raise ValueError("Positive ridge and at least two observations required")
        denominator=self.eigenvalues+alpha
        fitted=self.mean+self.train_left@(self.right/denominator[:,None])
        leverage=1/len(self.residual)+(self.leverage_features/denominator[None]).sum(1)
        return self.residual-(self.residual-fitted)/(1-leverage[:,None]).clamp_min(1e-7)


def reference_features(reference, train_ids, rank, power):
    # Remove common prompt difficulty; intercept later handles model ability.
    contrast = reference-reference.mean(1, keepdim=True)
    center = contrast[train_ids].mean(0, keepdim=True)
    centered = contrast-center
    covariance = centered[train_ids].T@centered[train_ids]/len(train_ids)
    eigenvalues, vectors = torch.linalg.eigh(covariance)
    rank = min(rank, len(eigenvalues)-1)
    vals, vecs = eigenvalues[-rank:].clamp_min(1e-6), vectors[:,-rank:]
    features = centered@vecs/(vals[None]**(power/2))
    # Total feature variance one: ridge scales comparable across rank/power.
    scale = features[train_ids].square().sum(1).mean().sqrt().clamp_min(1e-6)
    return features/scale
