"""Synthesize stereo effects placed on frame numbers from the film config."""

import argparse
import json
import struct
import wave
from math import exp, sin, tau
from pathlib import Path


RATE = 48000


def synthesize(config, output):
    fps = config["fps"]
    sample_count = round(config["frames"] * RATE / fps)
    mix = [0.0] * sample_count
    for cue in config["cues"]:
        start = round(cue["frame"] * RATE / fps)
        length = min(round(cue["seconds"] * RATE), sample_count - start)
        for i in range(length):
            t = i / RATE
            phase = tau * cue["hz"] * (t + 0.04 * (1 - exp(-38 * t)))
            envelope = min(1, t / 0.005) * exp(-5 * i / length)
            mix[start + i] += cue["gain"] * envelope * (0.78 * sin(phase) + 0.22 * sin(2.7 * phase))

    stereo = bytearray(sample_count * 4)
    for i, level in enumerate(mix):
        sample = round(max(-1, min(1, level)) * 32767)
        struct.pack_into("<hh", stereo, i * 4, sample, sample)
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as audio:
        audio.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
        audio.writeframes(stereo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    synthesize(json.loads(options.config.read_text(encoding="utf-8")), options.output)
