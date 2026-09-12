"""Flat K20/K100 geometry; no parent-child clusters are constructed."""

from audit.estimators import empirical_strength, fit_clusters
from .baselines import Episode
from .profiles import ProfileEpisode


class FlatEpisode(Episode):
    def __init__(self, arrays, seed):
        ProfileEpisode.__init__(self, arrays, seed)
        self.device = self.x.device
        tq, tm = self.idx["train_q"], self.idx["train_m"]
        train_y = self.y[tq][:, tm]
        self.labels, self.centers, self.strength = {}, {}, {}
        for k in (20, 100):
            center = fit_clusters(self.x[tq], k, seed+k)
            self.centers[k] = center
            self.labels[k] = (self.x@center.T).argmax(1)
            self.strength[k] = empirical_strength(self.labels[k][tq], train_y, k, train_y.mean(0))
