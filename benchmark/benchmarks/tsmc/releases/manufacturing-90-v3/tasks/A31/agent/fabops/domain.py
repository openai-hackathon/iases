"""Apply quality gating before an ordered spectral diagnostic pipeline."""
from .preprocess import fill, detrend
from .spectrum import window, energies

def run(request):
    values, coverage = fill(request["samples"], request["max_gap"])
    output = dict(coverage=round(coverage, 6), slope=None, band_energy=None,
                  total_energy=None, ratio=None, decision="insufficient_data")
    if values is None or coverage < request["min_coverage"]:
        return output
    windowed, normalizer = window(values)
    windowed, slope = detrend(windowed)
    energy, total = energies(windowed, normalizer, request["sample_rate"], request["band"])
    ratio = energy / total if total > 1e-12 else 0.0
    decision = ("alarm" if energy >= request["energy_threshold"]
                and ratio >= request["ratio_threshold"] else "normal")
    output.update(slope=round(slope, 6), band_energy=round(energy, 6),
                  total_energy=round(total, 6), ratio=round(ratio, 6), decision=decision)
    return output
