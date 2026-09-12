# Public behavior contract

Fit and apply a deterministic two-feature cycle monitor. Hydraulic source profiles
motivate the five condition fields, but these fixtures and fault scenarios are synthetic.
Each cycle has unique id, run (campaign id), start,end with end>start, features [x,y],
and profile [cooler,valve,pump_leakage,accumulator,stable_flag]. Known healthy conditions
are exactly [100,100,0,130]; stable_flag=0 means stable and 1 means possibly transient.
Finite feature values may be None for unavailable measurements. Input order is arbitrary.

request.target identifies one existing cycle. Other parameters are nonnegative embargo,
integer min_train>=2, shrinkage in [0.05,1], and nonnegative threshold. Select training cycles
only when their run differs from the target's ENTIRE run, end<=target.start-embargo,
stable_flag==0, ALL four component conditions are healthy, and neither feature is None.
Purge using the candidate END time, not start; equality at the embargo boundary is allowed.
Sort the selected rows by (end,id). Never train on future rows, target-run siblings,
transient rows, partially faulty profiles, or the target feature vector.

With fewer than min_train rows return their training ids, None for center,scale,correlation,
score and decision='insufficient_training'. Otherwise fit both coordinate means and
POPULATION variances on only those rows. Scale is sqrt(variance), or 1 for zero variance.
The raw correlation is mean((x-center_x)*(y-center_y))/(scale_x*scale_y), including zero
when either feature is constant. Store r=(1-shrinkage)*raw_correlation. This is shrinkage
of a standardized correlation matrix toward the identity, not a raw covariance matrix.

With z_j=(target_feature_j-center_j)/scale_j, score is the squared Mahalanobis distance
(z_x^2-2*r*z_x*z_y+z_y^2)/(1-r^2). Score the target even when its component labels are
unhealthy; labels are training eligibility only. If the target is transient or missing a
feature, still return the fitted model but score=None, decision='deferred'. Otherwise
decision is 'alarm' iff the UNROUNDED score>=threshold, else 'normal'. Return training ids,
center[2],scale[2],correlation,score,decision; round model numbers and score to six decimals
only for output. All fitting and scoring calculations use unrounded values. Inputs are immutable.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
