def run(request):
    tokens, last, accepted = request["capacity"] * 1000, 0, []
    for now in request["times"]:
        tokens = min(request["capacity"] * 1000, tokens + ((now - last) * request["rate"] // 1000) * 1000)
        last = now
        valid = tokens >= 1000
        if valid:
            tokens -= 1000
        accepted.append(valid)
    return dict(accepted=accepted, milli_tokens=tokens)
