"""Safe single-shot Wan2.2 TI2V-5B runner for a user-owned GPU Pod."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SIZE = "704*1280"
FPS = 24


class SmokeError(ValueError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def build_command(wan_root, model_dir, image, prompt, output, seconds, seed):
    seconds = int(seconds)
    if not 3 <= seconds <= 5:
        raise SmokeError("First paid GPU smoke must be 3-5 seconds")
    if not prompt.strip() or len(prompt) > 6000:
        raise SmokeError("Need a nonempty prompt up to 6000 characters")
    if not isinstance(seed, int) or seed < 0:
        raise SmokeError("Seed must be a nonnegative integer")
    image = Path(image).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    wan_root = Path(wan_root).expanduser().resolve()
    model_dir = Path(model_dir).expanduser().resolve()
    if image.suffix.lower() not in (".jpg", ".jpeg", ".png") or not image.is_file():
        raise SmokeError("Provide an existing approved PNG/JPEG reference frame")
    if image.stat().st_size > 40_000_000:
        raise SmokeError("Reference image exceeds 40MB")
    if output.suffix.lower() != ".mp4":
        raise SmokeError("Output must be MP4")
    if not (wan_root / "generate.py").is_file():
        raise SmokeError("Wan source not bootstrapped; run bootstrap.sh on Pod")
    if not model_dir.is_dir() or not any(model_dir.iterdir()):
        raise SmokeError("Wan checkpoint not downloaded")
    if output.exists():
        raise SmokeError("Output already exists; do not silently overwrite an earlier result")
    frame_num = seconds * FPS + 1  # 4n+1
    return [
      sys.executable, str(wan_root / "generate.py"),
      "--task", "ti2v-5B", "--size", SIZE, "--frame_num", str(frame_num),
      "--ckpt_dir", str(model_dir), "--offload_model", "True",
      "--convert_model_dtype", "--t5_cpu", "--image", str(image),
      "--prompt", prompt, "--base_seed", str(seed), "--save_file", str(output)
    ]


def inspect(path, seconds):
    try:
        info = subprocess.run([
            "ffprobe", "-v", "error", "-show_format", "-show_streams",
            "-of", "json", str(path)], check=True, capture_output=True,
            text=True, timeout=45)
        data = json.loads(info.stdout)
        video = next(s for s in data.get("streams", []) if s.get("codec_type") == "video")
        frames = int(video.get("nb_frames") or 0)
        duration = float(data.get("format", {}).get("duration") or 0)
        width, height = int(video["width"]), int(video["height"])
        if width < 640 or height < 1100 or not (seconds - .2 <= duration <= seconds + .5):
            raise SmokeError("Output is not the expected duration or portrait video format")
        return {"status": "VIDEO_RENDERED_REVIEW_REQUIRED",
                "duration_seconds": duration, "width": width, "height": height,
                "decoded_frame_count_reported": frames or None,
                "audio_present": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
                "sha256": sha256(path),
                "warnings": ["Wan2.2 TI2V-5B video generation does not prove audio exists.",
                             "Visual continuity, physics and rights require human review."]}
    except (OSError, subprocess.CalledProcessError, StopIteration, KeyError, ValueError) as exc:
        raise SmokeError("Could not verify video: " + type(exc).__name__) from None


def run(args):
    output = Path(args.output).expanduser().resolve()
    prompt = Path(args.prompt_file).read_text(encoding="utf8").strip()
    command = build_command(args.wan_root, args.model_dir, args.image, prompt,
                            output, args.seconds, args.seed)
    manifest = {"status": "DRY_RUN", "wan_task": "ti2v-5B",
                "model": "Wan-AI/Wan2.2-TI2V-5B", "seconds": args.seconds,
                "seed": args.seed, "input_sha256": sha256(args.image),
                "command": command[:]}
    if args.dry_run:
        return manifest
    if not args.approved_image:
        raise SmokeError("Human approval of the input image required (--approved-image)")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.total",
                          "--format=csv,noheader,nounits"], check=True,
                         capture_output=True, text=True, timeout=30)
    amounts = [int(x.strip()) for x in gpu.stdout.splitlines() if x.strip().isdigit()]
    if not amounts or max(amounts) < 24000:
        raise SmokeError("At least 24 GB nominal GPU VRAM required")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(command, cwd=Path(args.wan_root).resolve(),
                       check=True, timeout=5400)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SmokeError("Wan generation failed: " + type(exc).__name__) from None
    if not output.is_file() or not output.stat().st_size:
        raise SmokeError("Wan did not produce a nonempty MP4")
    manifest.update(inspect(output, args.seconds))
    manifest.pop("command", None)
    manifest["output"] = str(output)
    (output.parent / (output.stem + ".audit.json")).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--wan-root", default="/workspace/Wan2.2")
    parser.add_argument("--model-dir", default="/workspace/models/Wan2.2-TI2V-5B")
    parser.add_argument("--image", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=int, default=5, choices=[3, 4, 5])
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--approved-image", action="store_true",
                        help="Confirm real human preapproval of the reference frame")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(run(args), ensure_ascii=False, indent=2))
    except (SmokeError, OSError, subprocess.CalledProcessError) as exc:
        print("WAN_SMOKE ERROR: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
