from math import pi
from .segments import segments
from .welch import summarize

def run(request):
    first = request["samples"]
    second = request.get("reference", first)
    coverage = sum(a is not None and b is not None for a,b in zip(first,second))/len(first)
    selected = segments(request)
    output = dict(coverage=round(coverage,6), segments=[row[0] for row in selected],
                  slope=None,band_energy=None,total_energy=None,ratio=None,
                  reference_energy=None,coherence=None,phase=None,decision="insufficient_data")
    if len(selected) < 1:
        return output
    energy, total, reference_energy, coherence, phase = summarize(selected, request)
    ratio = energy/total if total > 1e-12 else 0.0
    slope = sum(row[3] for row in selected)/len(selected)
    decision = ("alarm" if energy >= request["energy_threshold"] and ratio >= request["ratio_threshold"]
                and coherence >= request.get("coherence_threshold",0)
                and abs(phase) <= request.get("phase_limit",pi) else "normal")
    output.update(slope=round(slope,6),band_energy=round(energy,6),total_energy=round(total,6),
                  ratio=round(ratio,6),reference_energy=round(reference_energy,6),
                  coherence=round(coherence,6),phase=round(phase,6),decision=decision)
    return output
