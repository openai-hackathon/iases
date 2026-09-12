# Public behavior contract

readings contains unique [time,value] pairs. For each query time choose the nearest reading within inclusive tolerance, breaking distance ties toward earlier time. Return value or None. Inputs may be unordered; queries retain their order. tolerance>=0.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
