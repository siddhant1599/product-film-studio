"""Check Blender's frame count and resolution, then pack PNGs as WebP plates."""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image


def prepare(config, source, output):
    names = [f"{index:06}" for index in range(config["frames"])]
    expected = {f"{name}.png" for name in names}
    actual = {p.name for p in source.glob("*.png")}
    if actual != expected:
        raise ValueError(f"Plate sequence mismatch: {len(expected - actual)} missing, {len(actual - expected)} extra")
    size = (config["width"], config["height"])
    output.mkdir(parents=True, exist_ok=True)

    def transcode(name):
        path = source / f"{name}.png"
        with Image.open(path) as image:
            if image.size != size:
                raise ValueError(f"{path.name} is {image.size}; expected {size}")
            image.convert("RGB").save(output / f"{name}.webp", "WEBP", quality=93, method=4)

    with ThreadPoolExecutor(max_workers=4) as pool:
        for _ in pool.map(transcode, names):
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    prepare(json.loads(options.config.read_text(encoding="utf-8")), options.source, options.output)
