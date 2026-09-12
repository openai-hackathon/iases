# Public behavior contract

Retry-After is either nonnegative integer seconds or an RFC 7231 HTTP date. now is an HTTP date in GMT. Return max(0, retry_time-now) seconds for dates, literal seconds for integers, and None for malformed or negative headers. Strip surrounding whitespace.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
