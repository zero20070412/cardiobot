from __future__ import annotations

import math
from typing import Sequence


def _generate_mock_ecg_waveform(num_points: int = 240) -> list[float]:
    """Generate a deterministic placeholder ECG-like waveform."""
    waveform: list[float] = []
    for index in range(num_points):
        phase = (index % 40) / 40
        baseline = 0.03 * math.sin(index / 6)

        if phase < 0.1:
            value = baseline + 0.05 * math.sin(phase * math.pi * 10)
        elif phase < 0.16:
            value = baseline - 0.08
        elif phase < 0.2:
            value = baseline + 1.0
        elif phase < 0.26:
            value = baseline - 0.12
        elif phase < 0.45:
            value = baseline + 0.18 * math.sin((phase - 0.26) * math.pi * 5)
        else:
            value = baseline

        waveform.append(round(value, 4))
    return waveform


def analyze_ecg(
    signal_data: Sequence[float] | None = None,
    sampling_rate: int = 250,
) -> dict[str, object]:
    """Return a mock ECG analysis result without running a real algorithm."""
    waveform = list(signal_data) if signal_data else _generate_mock_ecg_waveform()

    return {
        "module": "ecg",
        "status": "placeholder",
        "algorithm": "Pan-Tompkins (reserved, not enabled)",
        "summary": "ECG placeholder analysis completed. A stable sinus-rhythm-like mock result was returned for integration.",
        "risk_level": "low",
        "metrics": {
            "heart_rate_bpm": 72,
            "rhythm": "regular",
            "r_peak_count": 6,
            "signal_quality": "good",
        },
        "visualization": {
            "waveform": waveform,
            "sampling_rate": sampling_rate,
        },
        "meta": {
            "input_provided": bool(signal_data),
            "placeholder_only": True,
        },
    }


__all__ = ["analyze_ecg"]
