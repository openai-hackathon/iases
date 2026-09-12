# Public behavior contract

lines are journal records 'sequence|payload|crc', where crc is eight lowercase hexadecimal digits for zlib.crc32 of UTF-8 'sequence|payload'. Sequences start at 1 and are contiguous; payload has no pipes. Ignore at most one malformed or bad-checksum final line as a torn append. Malformed earlier lines or valid records with noncontiguous sequence raise ValueError. Return payloads of recovered records. A valid final record must never be discarded.

The entry point is `fabops.domain.run(request)`. Inputs are JSON-compatible. Do not mutate the request, including on rejected operations. Only the documented valid input domain is tested.
