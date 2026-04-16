from __future__ import annotations

import math
from typing import Sequence


def _generate_mock_pcg_waveform(num_points: int = 240) -> list[float]:
    """Generate a deterministic placeholder PCG-like waveform."""
    waveform: list[float] = []
    for index in range(num_points):
        phase = (index % 60) / 60
        baseline = 0.01 * math.sin(index / 8)

        if 0.08 <= phase < 0.14:
            value = baseline + 0.65 * math.sin((phase - 0.08) * math.pi * 16)
        elif 0.36 <= phase < 0.43:
            value = baseline + 0.45 * math.sin((phase - 0.36) * math.pi * 14)
        else:
            value = baseline

        waveform.append(round(value, 4))
    return waveform


def analyze_pcg(
    audio_data: Sequence[float] | None = None,
    sampling_rate: int = 2000,
) -> dict[str, object]:
    """Return a mock heart-sound analysis result without real PCG processing."""
    waveform = list(audio_data) if audio_data else _generate_mock_pcg_waveform()

    return {
        "module": "pcg",
        "status": "placeholder",
        "algorithm": "Heart sound analysis reserved, not enabled",
        "summary": "PCG placeholder analysis completed. A normal S1/S2-like mock result was returned for integration.",
        "risk_level": "low",
        "metrics": {
            "heart_sound_pattern": "normal_s1_s2",
            "murmur_risk": "low",
            "abnormal_sound_detected": False,
            "signal_quality": "good",
        },
        "visualization": {
            "waveform": waveform,
            "sampling_rate": sampling_rate,
        },
        "meta": {
            "input_provided": bool(audio_data),
            "placeholder_only": True,
        },
    }


__all__ = ["analyze_pcg"]
