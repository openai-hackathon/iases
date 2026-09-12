# Public behavior contract

baseline has at least two finite numbers. Compute its mean and sample standard deviation (n-1). Return booleans for measurements strictly outside mean +/- k*stdev; equality is in control. k>=0. Evaluation measurements must not change baseline statistics.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
