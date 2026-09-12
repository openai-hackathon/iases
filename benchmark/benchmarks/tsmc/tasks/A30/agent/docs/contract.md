# Public behavior contract

Fit a campaign-balanced hydraulic monitor for 1..5 feature coordinates. Cycles have
unique id, run, start,end (end>start), equally sized features of finite numbers or
None, and profile [cooler,valve,pump_leakage,accumulator,stable_flag]. Healthy is
[100,100,0,130] and stable_flag=0. target identifies an existing cycle. Select only
complete, healthy, stable rows from other runs with end<=target.start-embargo.
embargo>=0. Sort training by (end,id). min_train>=2 counts rows, not runs. No target
run member, future row, incomplete row or faulty component can enter training.

Give each selected run total weight 1/G and each of its n_g rows weight 1/(G*n_g).
Compute weighted means and population covariance, including between-run variation.
Scale_j=sqrt(cov_jj), or 1 when variance is zero. Correlation has diagonal 1 and
off-diagonal (1-shrinkage)*cov_jk/(scale_j*scale_k), shrinkage in [0.05,1].
Target labels do not affect eligibility to score except stable_flag. The optional
min_observed is 1..dimension, default dimension. Insufficient observed target
coordinates or a transient target gives deferred after model/calibration fitting.
Otherwise select the OBSERVED principal submatrix of correlation, solve R_obs*u=z,
and score=(dimension/observed_count)*dot(z,u). This uses the inverse of the observed
covariance submatrix, not the corresponding block of the full precision matrix;
do not impute missing target features. Use unrounded numbers throughout.

threshold>=0 is used unless calibrate=true. With calibration enabled, alpha is in
(0,1). For each run in the outer training cohort, hold out its ENTIRE run. Fit a
fresh model only on eligible outer rows from other runs ending no later than
min(held_run.start)-embargo. Skip a run when its fresh training has fewer than
min_train rows. Score every held row with that model and retain their MAX score
as one calibration observation. Sort returned [run,score] pairs by run. For m
observations, take one-based rank ceil((m+1)*(1-alpha)) of ascending raw scores.
If m=0 or rank>m, threshold=None. No interpolation or clipping of rank is allowed.

Return training,center,scale,correlation (a matrix),score,calibration,threshold,
decision. Insufficient outer training gives all numerical fields None, calibration=[]
and decision=insufficient_training. Otherwise fit and calibrate, then defer an
unscorable target; else report its score and insufficient_calibration if threshold
is None, alarm iff raw score>=raw threshold, otherwise normal. Round reported
numbers to six decimals only. At most 24 cycles. Inputs must remain unchanged.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
