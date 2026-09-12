import numpy as np

from research40.exact_frontier import evaluate_exact


def paper_metrics(prediction, quality, costs):
    result = evaluate_exact(prediction, quality, costs)
    costs = np.asarray(costs, dtype=np.float64)
    lower, upper = float(costs.min()), float(costs.max())
    cap = max(lower, .5*upper)
    x, y = np.asarray(result['cost']), np.asarray(result['accuracy'])
    selected = x < cap
    xx = np.r_[x[selected], cap]
    yy = np.r_[y[selected], np.interp(cap, x, y)]
    result['area50'] = float(np.sum(np.diff(xx)*(yy[:-1]+yy[1:])/2)/(upper-lower)) if upper > lower else 0.
    result['normalized_cost'] = ((x-lower)/(upper-lower)).tolist() if upper > lower else [0.]*len(x)
    result['peak_accuracy'] = float(y.max())
    return result
