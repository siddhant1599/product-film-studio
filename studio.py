"""Build, inspect, and export the sample film. Run with the project's Python venv."""

import argparse
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from string import Template
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "film.json"
BUILD = ROOT / "build"
PLATES = BUILD / "plates"
COMP = BUILD / "composition"
ASSETS = COMP / "assets"
STAGES = ROOT / "stages"
NODE_MODULES = ROOT / "node_modules"


def run(*command):
    subprocess.run(command, cwd=ROOT, check=True)


def hf(*args):
    if not (NODE_MODULES / "hyperframes").is_dir():
        raise ValueError("HyperFrames is not installed. Run npm ci first.")
    # npm's Windows shim is a .cmd file; the package's JS entry point works on both.
    package = NODE_MODULES / "hyperframes"
    metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
    entry = metadata["bin"]
    run("node", package / (entry["hyperframes"] if isinstance(entry, dict) else entry), *args)


def config_values():
    values = json.loads(CONFIG.read_text(encoding="utf-8"))
    for key in ("width", "height", "fps", "frames", "cycles_samples", "reveal_frame"):
        if type(values[key]) is not int or values[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if values["width"] % 2 or values["height"] % 2:
        raise ValueError("width and height must be even for H.264")
    if values["fps"] > 240 or values["reveal_frame"] >= values["frames"]:
        raise ValueError("fps must be at most 240 and reveal_frame must be inside the clip")
    for cue in values["cues"]:
        if type(cue["frame"]) is not int or not 0 <= cue["frame"] < values["frames"]:
            raise ValueError("Each audio cue needs an integer frame index inside the clip")
        if cue["hz"] <= 0 or cue["seconds"] <= 0 or not 0 <= cue["gain"] <= 1:
            raise ValueError("Audio cues need a positive frequency and duration, and gain from 0 to 1")
    return values


def replace_dir(source, target):
    if target.exists():
        shutil.rmtree(target)
    source.rename(target)


def plates():
    BUILD.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=BUILD) as work:
        frames = Path(work) / "plates"
        run(
            os.environ.get("BLENDER") or "blender",
            "--background", "--factory-startup", "--python-exit-code", "1",
            "--python", STAGES / "render_plates.py", "--", CONFIG, frames,
        )
        replace_dir(frames, PLATES)


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=ASSETS) as work:
        frames = Path(work) / "plates"
        run(sys.executable, STAGES / "prepare_plates.py", CONFIG, PLATES, frames)
        replace_dir(frames, ASSETS / "plates")


def sound():
    run(sys.executable, STAGES / "sound.py", CONFIG, ASSETS / "effects.wav")


def assemble(config):
    if not (ASSETS / "plates").is_dir() or not (ASSETS / "effects.wav").is_file():
        raise ValueError("Run prepare and sound (or build) before assembling.")
    gsap = NODE_MODULES / "gsap"
    font = NODE_MODULES / "@fontsource-variable" / "manrope"
    if not gsap.is_dir() or not font.is_dir():
        raise ValueError("Run npm ci to install GSAP and Manrope before assembling.")
    shutil.copyfile(gsap / "dist" / "gsap.min.js", ASSETS / "gsap.min.js")
    shutil.copyfile(font / "files" / "manrope-latin-wght-normal.woff2", ASSETS / "manrope-latin.woff2")
    shutil.copyfile(font / "LICENSE", ASSETS / "manrope-LICENSE.txt")
    source = ROOT / "composition"
    for name in ("film.css", "film.js"):
        shutil.copyfile(source / name, COMP / name)
    fields = {key: html.escape(str(value)) for key, value in config.items()}
    fields["duration"] = str(config["frames"] / config["fps"])
    template = Template((source / "index.html.in").read_text(encoding="utf-8"))
    (COMP / "index.html").write_text(template.substitute(fields), encoding="utf-8")


def require_composition():
    if not (COMP / "index.html").is_file():
        raise ValueError("Run build before checking, previewing or exporting.")


def check():
    require_composition()
    hf("lint", COMP)
    hf("check", COMP, "--json")


def export(config, quality):
    require_composition()
    hf("render", COMP, "--fps", str(config["fps"]), "--quality", quality, "-o", BUILD / "film.mp4")


def build(config):
    plates()
    prepare()
    sound()
    assemble(config)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True)
    for stage in ("plates", "prepare", "sound", "assemble", "build", "check"):
        commands.add_parser(stage)
    preview = commands.add_parser("preview")
    preview.add_argument("--port", type=int, default=3002)
    lifecycle = preview.add_mutually_exclusive_group()
    lifecycle.add_argument("--background", action="store_true")
    lifecycle.add_argument("--stop", action="store_true")
    preview.add_argument("--no-open", action="store_true")
    for stage in ("export", "all"):
        subcommand = commands.add_parser(stage)
        subcommand.add_argument("--quality", choices=("draft", "looks", "delivery"), default="looks")
    args = parser.parse_args()

    try:
        config = config_values()
        if args.stage in ("build", "all"):
            build(config)
        if args.stage in ("check", "all", "export"):
            check()
        if args.stage in ("export", "all"):
            export(config, args.quality)
        if args.stage == "preview":
            require_composition()
            mode = "--stop" if args.stop else "--background" if args.background else "--foreground"
            hf("preview", COMP, "--port", str(args.port), mode, *(["--no-open"] if args.no_open else []))
        if args.stage == "assemble":
            assemble(config)
        if args.stage in ("plates", "prepare", "sound"):
            {"plates": plates, "prepare": prepare, "sound": sound}[args.stage]()
    except subprocess.CalledProcessError as error:
        return error.returncode or 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"studio: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
