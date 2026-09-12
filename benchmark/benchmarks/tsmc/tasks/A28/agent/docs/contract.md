# Public behavior contract

planned>0 and 0<runtime<=planned are seconds. lots has total, good and ideal_cycle seconds per unit, with total>0, 0<=good<=total, ideal_cycle>0. Compute availability=runtime/planned, performance=sum(total*ideal_cycle)/runtime, quality=sum(good)/sum(total), and oee=their product. Do not clamp performance. Lots is nonempty. Test values are exactly representable.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
