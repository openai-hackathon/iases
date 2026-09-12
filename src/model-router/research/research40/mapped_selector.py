import numpy as np


class MappedSelector:
    def __init__(self, path):
        with np.load(path, allow_pickle=False) as data:
            self.layers = [(data[f'w{i}'], data[f'b{i}']) for i in range(3)]
            self.profile = data['profile']
            self.offset = data['offset']
            self.table = data['table']
            self.centers = data['centers']
            self.models = data['models'].tolist()
            self.costs = data['costs']
        size = len(self.models)
        if self.layers[0][0].ndim != 2:
            raise ValueError('Invalid network input array')
        dimensions = self.layers[0][0].shape[1]
        for weights, bias in self.layers:
            if not dimensions or weights.ndim != 2 or not len(weights) or weights.shape[1] != dimensions or bias.shape != (len(weights),):
                raise ValueError('Incompatible network arrays')
            dimensions = len(weights)
        if not size or not all(isinstance(name, str) and name for name in self.models) or len(set(self.models)) != size or self.profile.shape != (dimensions, size) or self.offset.shape != (size,) or self.costs.shape != (size,) or self.centers.ndim != 2 or not len(self.centers) or self.centers.shape[1] != self.layers[0][0].shape[1] or self.table.shape != (len(self.centers), size):
            raise ValueError('Incompatible profile arrays')
        arrays = [value for layer in self.layers for value in layer] + [self.profile, self.offset, self.table, self.centers, self.costs]
        if not all(np.isfinite(value).all() for value in arrays) or np.any(self.costs < 0):
            raise ValueError('Invalid artifact values')

    def scores(self, query):
        query = np.asarray(query, dtype=np.float64)
        if query.shape != (self.centers.shape[1],) or not np.isfinite(query).all():
            raise ValueError('Invalid query')
        norm = np.linalg.norm(query)
        if abs(norm-1) > 1e-3:
            raise ValueError('Expected a normalised embedding')
        value = query
        for weights, bias in self.layers[:2]:
            value = np.maximum(weights @ value + bias, 0)
        value = self.layers[2][0] @ value + self.layers[2][1]
        probability = np.exp(value-value.max())
        probability /= probability.sum()
        cell = (self.centers @ (query/norm)).argmax()
        return np.clip(probability @ self.profile + self.offset + self.table[cell], 0, 1)

    def select(self, query, weight=0., candidates=None):
        if not np.isfinite(weight) or weight < 0:
            raise ValueError('Invalid cost weight')
        ids = np.arange(len(self.models)) if candidates is None else np.array([self.models.index(name) for name in candidates], dtype=int)
        if not len(ids):
            raise ValueError('No eligible models')
        quality = self.scores(query)
        chosen = ids[(quality[ids]-weight*self.costs[ids]).argmax()]
        return dict(model=self.models[chosen], quality=float(quality[chosen]), cost=float(self.costs[chosen]))

    def method(self):
        return 'hiershrink-frozen-learnedmap'

    def update_feedback(self, feedback):
        raise NotImplementedError('Rebuild the profile artifact offline')
