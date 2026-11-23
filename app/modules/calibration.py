"""Pick the noise gate and frame thresholds from a short recording.

The user is silent for a few seconds, then talks. Levels are sampled with
noise suppression and the compressor turned off, so they are raw 0-100 values
(see audio_manager). The fixed noise gate sits above the background noise and
frame thresholds are spread over the gated speech levels.
"""
from dataclasses import dataclass
from typing import List, Sequence

GATE_MARGIN = 6.0
MIN_GATE = 5
MAX_GATE = 60
MIN_STEP = 3
MIN_VOICED_SAMPLES = 15


class CalibrationError(Exception):
    pass


@dataclass
class Calibration:
    noise_level: float
    gate: int
    thresholds: List[int]


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * min(max(q, 0.0), 100.0) / 100.0
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def gated(level: float, gate: float) -> float:
    """Same mapping as audio_manager's fixed noise gate."""
    if level <= gate:
        return 0.0
    return min((level - gate) * 100.0 / max(100.0 - gate, 1.0), 100.0)


def analyze(silence: Sequence[float], speech: Sequence[float], frame_count: int) -> Calibration:
    if not silence or not speech:
        raise CalibrationError("not enough samples")
    noise = percentile(silence, 95)
    gate = int(round(min(max(noise + GATE_MARGIN, MIN_GATE), MAX_GATE)))
    voiced = [gated(level, gate) for level in speech if level > gate]
    if len(voiced) < MIN_VOICED_SAMPLES:
        raise CalibrationError("speech too quiet")

    thresholds = [0]
    count = max(frame_count, 1)
    if count >= 2:
        # Quiet speech already opens the mouth; the loudest frame needs a real raise of the voice.
        quantiles = [15.0] if count == 2 else [15 + 70 * i / (count - 2) for i in range(count - 1)]
        for q in quantiles:
            value = int(round(percentile(voiced, q)))
            thresholds.append(min(max(value, thresholds[-1] + MIN_STEP), 100))
    return Calibration(noise_level=round(noise, 1), gate=gate, thresholds=thresholds)
