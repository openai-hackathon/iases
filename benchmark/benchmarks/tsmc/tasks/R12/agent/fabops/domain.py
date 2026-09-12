def run(request):
    processed, dead, attempts = [], [], {}
    for message in request["messages"]:
        key = message["id"]
        attempts[key] = 1 if message["valid"] else request["max_attempts"]
        if message["valid"]:
            processed.append(key)
        else:
            dead.append(key)
            break
    return dict(processed=processed, dead_letter=dead, attempts=attempts)
