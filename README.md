# Product Film Studio

Generate a product film from source: **Blender Cycles → PNG frames → WebP plates + synthetic WAV → GSAP/HyperFrames → H.264/AAC MP4.** The included two-second sample assembles a geometric object in a studio shot. It's a small test of the pipeline, not a finished film or a set of client projects.

## 1. Install

Install [Blender 4.5 LTS](https://www.blender.org/download/lts/4-5/), [Node.js 22 LTS](https://nodejs.org/), [Python 3.10 or newer](https://www.python.org/downloads/), and [FFmpeg 7 or newer](https://ffmpeg.org/download.html) with `ffmpeg` and `ffprobe` on PATH. The sample uses CPU Cycles; no Blender add-ons, account, API key, or GPU are required.

From this folder, with a POSIX shell (Linux/macOS):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
npm ci
npx --no-install hyperframes browser ensure
```

Use `blender --version` to check that Blender is on PATH. If it isn't, set `BLENDER` to the full executable path (on macOS, typically `export BLENDER=/Applications/Blender.app/Contents/MacOS/Blender`). HyperFrames' browser installation may require system libraries on a minimal Linux host; see its [installation guide](https://hyperframes.heygen.com/quickstart).

## 2. Build the sample

```sh
python studio.py build
```

Or run the same stages individually to inspect or regenerate an intermediate:

| Command | Stage | Output |
| --- | --- | --- |
| `python studio.py plates` | Build the procedural Blender scene and render it with Cycles | `build/plates/*.png` |
| `python studio.py prepare` | Verify frame numbering and dimensions, then convert each PNG with Pillow | `build/composition/assets/plates/*.webp` |
| `python studio.py sound` | Synthesize frame-aligned effects in Python | `build/composition/assets/effects.wav` |
| `python studio.py assemble` | Set composition size and timing, and stage HTML/CSS/JS, GSAP and the font | `build/composition/index.html` and local assets |

## 3. Check, preview, and export

```sh
python studio.py check
python studio.py preview  # Opens HyperFrames Studio; Ctrl+C stops the server
```

After closing the preview, export:

```sh
python studio.py export
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,sample_rate,channels,duration build/film.mp4
```

The default sample is 960×540 at 24 fps, with 48 H.264 frames and two seconds of stereo AAC audio. `export` runs the checks before encoding. For a non-interactive build, `python studio.py all` builds, checks, and exports without opening Studio. Append `--quality draft` for a quick iteration or `--quality delivery` for the higher-quality encode.

## Adapt it for another film

- **Timing:** Set dimensions, integer frame rate, frame count, copy, and cue frames in `film.json`. Frame numbers start at zero. The lid lands, its cue plays, and the accent line draws in at frame 22 in the sample. If you move the landing, move its audio cue to the same frame.
- **3D:** Replace the procedural scene in `stages/render_plates.py` or adapt the Blender command to load your own `.blend`. Keep an uninterrupted, zero-based sequence at the configured size, or adjust `prepare_plates.py` to match your renderer. For a 1080p job set width and height to 1920 and 1080 and tune `cycles_samples` for your scene.
- **Sound:** Edit the cue list or the synthesis in `stages/sound.py`. To use recorded effects or music instead, stage a cleared WAV at the same path, or add new local, timed `<audio class="clip">` assets in the composition.
- **Compositing:** Edit the template, stylesheet, and GSAP timeline in `composition/`, not the generated copy under `build/`. The paused timeline selects the matching plate when HyperFrames seeks; CSS layers the typography above it. Manrope (SIL OFL) and GSAP are installed via npm and staged locally, including Manrope's license and GSAP's original header. Use a cleared, locally hosted font if you substitute another typeface.
- **Scaling up:** This sample preloads every plate to make arbitrary seeks work in Studio. Decoded frames take roughly width × height × four bytes per frame per browser worker. For long or high-resolution shots split the sequence into shorter shots, or encode the plates as a local edit-friendly video and use a timed HyperFrames video clip. Keep that intermediate in `build/`.

After changing scene settings, rebuild from the relevant stage onward. For copy or layout edits alone, `python studio.py assemble` is enough. Everything generated is under the ignored `build/` directory; remove it for a clean run. Commit the source and lockfile, not dependencies, renders, or intermediate media.
