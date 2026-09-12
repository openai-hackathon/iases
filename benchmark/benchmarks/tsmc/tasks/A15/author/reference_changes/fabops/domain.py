def run(request):
    sessions = []
    for time in sorted(set(request["times"])):
        if sessions and time - sessions[-1][1] <= request["gap"]:
            sessions[-1][1] = time
            sessions[-1][2] += 1
        else:
            sessions.append([time, time, 1])
    return sessions
