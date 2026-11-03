"""10s MuseSteamer fallback: two REAL 5s tasks bridged by the first clip's last frame.

Each paid POST requires --confirm-two-paid; no retries on unknown task state.
Never call this from tests without a fully mocked submit/resume.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .core import FlowError, assemble, audit, config, create, load_json, now, save_json
from .platforms import make_package
from . import qianfan_i2v as i2v


MODEL = "musesteamer-air-i2v"


def last_frame(source_video, output_png):
    """Real extracted frame, not a fabricated still or new AI image."""
    if not Path(source_video).is_file():
        raise FlowError("Missing first 5s clip; no second paid request.")
    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-sseof", "-0.12", "-i", str(source_video),
        "-frames:v", "1", str(output_png)
    ], capture_output=True, timeout=60, check=False)
    if result.returncode or not output_png.is_file() or output_png.stat().st_size < 64:
        raise FlowError("Could not extract real end-frame; second POST NOT submitted")
    return output_png


def make_10s(brief, first_frame, out_root, *, confirm_two_paid=False):
    """One logical 10s project, two separately tracked real provider calls.

    An error stops immediately and leaves any completed part in out_root for
    manual inspection/reconciliation. Never repeat a partly completed job.
    """
    if not confirm_two_paid:
        raise FlowError("Two billable 5s tasks require --confirm-two-paid")
    root = Path(out_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise FlowError("Output already exists; do not repeat billable jobs")
    root.mkdir(parents=True, exist_ok=True)
    status = root / "progress.json"
    progress = {
        "workflow": "muse_5s_plus_5s_real_end_frame",
        "model": MODEL, "expected_total_seconds": 10,
        "paid_submissions_authorized": 2, "parts": [],
        "status": "STARTING", "created_at": now(),
        "publication_status": "NOT_SUBMITTED"
    }
    save_json(status, progress)
    stage_root = root / "stages"
    stage_root.mkdir(exist_ok=True)

    for index in (1, 2):
        source_frame = first_frame if index == 1 else str(root / "S02-tail.png")
        prompt = (brief if index == 1 else
                  "CONTINUE the exact same car and highway from the final frame "
                  "without resetting the scene. The same supercar is already moving "
                  "at high speed; wheels rotate, road scrolls backwards, stronger "
                  "acceleration and realistic perspective. Preserve identity. " + brief)
        part = i2v.plan(prompt, source_frame, seconds=5, ratio="1:1",
                        model=MODEL, resolution="720p",
                        sound="synthetic", platforms=(), out_root=stage_root,
                        enable_watermark=False)
        progress["parts"].append({
            "index": index, "job_folder": str(part.relative_to(root)),
            "state": "PLANNED", "task_id": None
        })
        save_json(status, progress)
        # submit_once stores the attempt marker BEFORE the provider POST.
        progress["parts"][-1]["state"] = "SUBMISSION_ATTEMPTED"
        save_json(status, progress)
        i2v.submit_once(part, confirm_paid=True)
        part_manifest = load_json(part / "manifest.json")
        progress["parts"][-1]["task_id"] = part_manifest["qianfan_i2v"].get("task_id")
        progress["parts"][-1]["state"] = "VIDEO_PENDING"
        save_json(status, progress)
        outcome = i2v.resume(part)
        if outcome != "AWAITING_HUMAN_REVIEW":
            progress["status"] = "PART_PENDING_OR_BLOCKED"
            save_json(status, progress)
            raise FlowError("Part not finalized. Do NOT repeat model POST; reconcile task_id")
        refreshed_manifest = load_json(part / "manifest.json")
        progress["parts"][-1]["task_id"] = refreshed_manifest["qianfan_i2v"].get("task_id")
        if not progress["parts"][-1]["task_id"]:
            raise FlowError("Confirmed part task ID missing after completion")
        progress["parts"][-1]["state"] = "VIDEO_COMPLETED_UNREVIEWED"
        save_json(status, progress)
        raw = part / "media" / "S01-qianfan-raw.mp4"
        if index == 1:
            last_frame(raw, root / "S02-tail.png")

    movie = create(brief, 10, "1:1", ["douyin"], root, config())
    movie_manifest = load_json(movie / "manifest.json")
    movie_media = movie / "media"
    movie_media.mkdir(exist_ok=True)
    for index, stage in enumerate(progress["parts"], start=1):
        part = root / stage["job_folder"]
        shot = movie_manifest["shots"][index - 1]
        name = f"S{index:02d}"
        raw = movie_media / f"{name}-qianfan-raw.mp4"
        shutil.copy2(part / "media" / "S01-qianfan-raw.mp4", raw)
        audio = movie_media / f"{name}-original-engine.wav"
        shutil.copy2(part / "media" / "original-engine-synth.wav", audio)
        shot["video"] = str(raw.relative_to(movie))
        shot["audio"] = str(audio.relative_to(movie))
        shot["state"] = "VIDEO_GENERATED_UNREVIEWED"
        shot["model_provenance"]["video"] = MODEL
        shot["model_provenance"]["audio"] = "original_synthetic_engine_not_real_vehicle_recording"
    save_json(movie / "manifest.json", movie_manifest)
    finished = assemble(movie, movie_manifest, config())
    i2v._watermark_mp4(finished)
    qc = audit(movie, movie_manifest, config(), finished)
    movie_manifest["render"] = str(finished.relative_to(movie))
    movie_manifest["qc"] = "qc.json"
    movie_manifest["status"] = "BLOCKED" if qc["status"] == "FAIL" else "AWAITING_HUMAN_REVIEW"
    movie_manifest["source_provenance"] = {
        "two_real_muse_tasks": [p["task_id"] for p in progress["parts"]],
        "bridge_frame": "S02-tail.png",
        "not_native_10s": True
    }
    save_json(movie / "manifest.json", movie_manifest)
    export = movie / "release-package"
    export.mkdir(exist_ok=True)
    save_json(export / "douyin.json", make_package(movie_manifest, "douyin"))
    progress["status"] = movie_manifest["status"]
    progress["final_job"] = str(movie.relative_to(root))
    save_json(status, progress)
    return movie


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True)
    parser.add_argument("--first-frame-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--confirm-two-paid", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = make_10s(args.brief, args.first_frame_file, args.out,
                          confirm_two_paid=args.confirm_two_paid)
        print(json.dumps({"video_job": str(result),
                          "status": load_json(result / "manifest.json")["status"]},
                         ensure_ascii=False))
        return 0
    except (FlowError, i2v.MediaTaskError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("MUSE 10s STOP: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
