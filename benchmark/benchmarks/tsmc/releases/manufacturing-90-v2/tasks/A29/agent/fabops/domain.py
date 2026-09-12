"""Report cycle work only when jointly supported measurements cover enough time."""
from .integrate import joint_integrals
from .segments import segments

def run(request):
    output = []
    for cycle in sorted(request["cycles"], key=lambda row: (row["start"], row["id"])):
        pressure = segments(request["pressure"], cycle, request["calibration"]["pressure"],
                            request["max_gap"]["pressure"])
        flow = segments(request["flow"], cycle, request["calibration"]["flow"],
                        request["max_gap"]["flow"])
        duration, volume, work = joint_integrals(pressure, flow)
        coverage = min(sum(s[1] - s[0] for s in pressure), sum(s[1] - s[0] for s in flow)) / (cycle["end"] - cycle["start"])
        accepted = duration > 0 and coverage >= request["min_coverage"]
        output.append(dict(cycle=cycle["id"], coverage=round(coverage, 6),
                           accepted=accepted,
                           volume=round(volume, 6) if accepted else None,
                           work=round(work, 6) if accepted else None))
    return output
