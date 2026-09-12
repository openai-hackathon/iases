"""Typed command identities exclude transport metadata."""
import json
from decimal import Decimal

def normalize(value):
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, (int, float)):
        number = Decimal(str(value))
        sign, digits, exponent = number.as_tuple()
        digits = list(digits)
        if not any(digits):
            return ["number", 0, [0], 0]
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        return ["number", sign, digits, exponent]
    if isinstance(value, str):
        return ["string", value]
    if isinstance(value, list):
        return ["array", sorted([normalize(item) for item in value], key=repr)]
    return ["object", [[key, normalize(value[key])] for key in sorted(value)]]

def fingerprint(command):
    return json.dumps(normalize([command["expected"], command["value"]]), separators=(",", ":"))

def scope_key(scope):
    return json.dumps(scope, separators=(",", ":"))
