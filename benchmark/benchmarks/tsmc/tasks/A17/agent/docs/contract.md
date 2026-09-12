# Public behavior contract

points is a list of [x,y]. Rotate counterclockwise by turns quarter turns about the origin, then translate by [dx,dy]. turns is any integer, including negative. Return transformed points in order.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
