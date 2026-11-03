"""35-second MuseSteamer Air storyboard: 7 x REAL 5-second clips with end-frame continuation.

Each paid POST is manually authorized for up to 7 independent tasks. No retry
after any uncertain or failed submission. Every clip has a separately recorded
task ID, provenance, and the next clip's actual extracted last-frame reference.

This is stitched 7x5s footage, never falsely claimed as native 35-second output.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import qianfan_i2v as i2v
from .core import FlowError, assemble, audit, config, create, load_json, now, save_json
from .platforms import make_package
from .muse_10s import last_frame

MODEL = "musesteamer-air-i2v"
SEGMENT_SECONDS = 5
SEGMENTS = 7
TOTAL_SECONDS = 35

# A single, continuous vehicle identity and environmental palette with
# progressive action; no teleportation, shot reset, or speculative car specs.
BEATS = (
    "0-5s: immediate ignition and physically clear launch; low front quarter tracking, wheels rotate and asphalt moves backward.",
    "5-10s: accelerate much faster while maintaining exact chassis, color, headlights, wheels and single vehicle; sweeping roadside parallax.",
    "10-15s: maintain forward road motion, closer low-angle tracking with visible wheel rotation; sunset reflections sweep continuously.",
    "15-20s: long straight opens up, faster credible tracking camera, road markings streak back; no camera teleport or second car.",
    "20-25s: side tracking captures dramatic acceleration and suspension response; never change wheel count or car silhouette.",
    "25-30s: rear-quarter view grows naturally as camera eases behind; realistic red tail lights and strong moving perspective.",
    "30-35s: exact same car continues along the same road and recedes toward the sunset; controlled cinematic finish, no stop."
)


def _bridge_prompt(index, brief):
    beat = BEATS[index - 1]
    continuity = (
        "EXACT SAME dark graphite silver hypercar and sunset road. "
        "Continue the physical motion at the exact preceding end-frame; "
        "no reset or jump cut, no new vehicle or redesigned body. "
        "Real spinning wheels, forward acceleration, stable proportions. "
    ) if index > 1 else (
        "Single dark graphite silver concept supercar, cinematic sunset road. "
        "Establish exact vehicle identity, real wheel rotation and forward motion. "
    )
    # Build-prompt has a 950-character brief guard, avoid failing after paid clips.
    text = continuity + beat + " Original idea: " + brief
    if len(text) > 925:
        raise FlowError("Creative brief too long for safe 35s continuity prompts")
    return text


def _portrait_from_square(source, dest):
    """Fill a 9:16 frame with an image-derived *blurred* backdrop, never black bars.

    Keep the whole original 1:1 video in the foreground; do not stretch the car
    or claim that provider delivered native 9:16 footage.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    filtergraph = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,boxblur=30:2[blur];"
        "[fg]scale=1080:1080:force_original_aspect_ratio=decrease[sharp];"
        "[blur][sharp]overlay=(W-w)/2:(H-h)/2:shortest=1,setsar=1[out]"
    )
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(source), "-filter_complex", filtergraph,
         "-map", "[out]", "-an", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "19", "-pix_fmt", "yuv420p", str(dest)],
        capture_output=True, timeout=240, check=False,
    )
    if result.returncode or not dest.is_file() or dest.stat().st_size < 256:
        raise FlowError("Portrait adaptation failed; no media is marked complete")
    return dest


def make_35s(brief, first_frame, out_root, *, confirm_seven_paid=False):
    """Generate exactly seven 5s clips, one POST per clip; never blind retry."""
    if not confirm_seven_paid:
        raise FlowError("Seven billable MuseSteamer tasks require --confirm-seven-paid")
    if not isinstance(brief, str) or not 4 <= len(brief.strip()) <= 500:
        raise FlowError("Provide a public, 4-500-character fictional racing brief")
    # Validate all seven prompts before the first request, not after spending.
    prompts = [_bridge_prompt(i, brief.strip()) for i in range(1, SEGMENTS + 1)]
    source = Path(first_frame).resolve()
    if not source.is_file() or source.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise FlowError("Approved local first-frame image missing")
    root = Path(out_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise FlowError("Existing 35s job: do NOT restart. Reconcile task IDs offline.")
    root.mkdir(parents=True, exist_ok=True)
    report = root / "progress.json"
    progress = {
        "model": MODEL, "workflow": "seven_5s_continuous_end_frame",
        "expected_clips": SEGMENTS, "expected_total_seconds": TOTAL_SECONDS,
        "paid_tasks_approved_max": SEGMENTS, "parts": [],
        "status": "STARTING", "started_at": now(),
        "published": False, "publication_status": "NOT_SUBMITTED",
        "ratio_note": "Provider frames may be square. Deliver a portrait adaptation with blurred image background; no stretching."
    }
    save_json(report, progress)
    stages = root / "stages"
    stages.mkdir(exist_ok=True)

    for index, prompt in enumerate(prompts, start=1):
        frame = source if index == 1 else root / f"S{index:02d}-start-from-prior-tail.png"
        if not frame.is_file():
            raise FlowError(f"Missing verified transition frame before clip {index}; no paid request")
        job = i2v.plan(prompt, str(frame), seconds=5, ratio="1:1",
                       model=MODEL, resolution="720p", sound="synthetic",
                       platforms=(), out_root=stages, enable_watermark=False)
        entry = {"segment": index, "seconds": 5,
                 "job_folder": str(job.relative_to(root)),
                 "state": "PLANNED", "task_id": None,
                 "transition_frame": str(frame.relative_to(root)) if index > 1 else "original_s01"}
        progress["parts"].append(entry)
        save_json(report, progress)
        entry["state"] = "SUBMISSION_ATTEMPTED"
        save_json(report, progress)
        # submit_once itself writes its attempted marker before the HTTP POST.
        # Even if the POST times out, the attempt remains recorded. No rerun.
        try:
            i2v.submit_once(job, confirm_paid=True)
        finally:
            task = load_json(job / "manifest.json").get("qianfan_i2v", {})
            entry["task_id"] = task.get("task_id")
            entry["state"] = task.get("status", "SUBMISSION_UNCERTAIN")
            save_json(report, progress)
        outcome = i2v.resume(job)
        if outcome != "AWAITING_HUMAN_REVIEW":
            progress["status"] = "PAUSED_PENDING_OR_BLOCKED"
            save_json(report, progress)
            raise FlowError(f"Clip {index} is not finalized. Reconcile recorded task ID; never retry POST.")
        task = load_json(job / "manifest.json")["qianfan_i2v"]
        entry["task_id"] = task.get("task_id")
        if not entry["task_id"]:
            raise FlowError(f"Clip {index} missing confirmed task ID after resume")
        entry["state"] = "VIDEO_COMPLETED_UNREVIEWED"
        save_json(report, progress)
        raw = job / "media" / "S01-qianfan-raw.mp4"
        if not raw.is_file():
            raise FlowError(f"Clip {index} finalized but has no provider MP4")
        if index < SEGMENTS:
            last_frame(raw, root / f"S{index+1:02d}-start-from-prior-tail.png")

    film = create(brief, TOTAL_SECONDS, "9:16", ["douyin"], root, config())
    manifest = load_json(film / "manifest.json")
    if len(manifest["shots"]) != SEGMENTS:
        raise FlowError("OneFlow did not allocate exactly seven shots")
    media = film / "media"
    media.mkdir(exist_ok=True)
    for i, entry in enumerate(progress["parts"], start=1):
        part = root / entry["job_folder"]
        raw = part / "media" / "S01-qianfan-raw.mp4"
        shutil.copy2(raw, media / f"S{i:02d}-provider-square.mp4")
        adapted = _portrait_from_square(raw, media / f"S{i:02d}-portrait.mp4")
        audio = media / f"S{i:02d}-engine.wav"
        shutil.copy2(part / "media" / "original-engine-synth.wav", audio)
        shot = manifest["shots"][i-1]
        shot["video"] = str(adapted.relative_to(film))
        shot["audio"] = str(audio.relative_to(film))
        shot["state"] = "VIDEO_GENERATED_UNREVIEWED"
        shot["model_provenance"]["video"] = MODEL
        shot["model_provenance"]["audio"] = "original_ffmpeg_synthetic_engine_not_recording"

    save_json(film / "manifest.json", manifest)
    result = assemble(film, manifest, config())
    i2v._watermark_mp4(result)
    qc = audit(film, manifest, config(), result)
    manifest["render"] = str(result.relative_to(film))
    manifest["qc"] = "qc.json"
    manifest["status"] = "BLOCKED" if qc["status"] == "FAIL" else "AWAITING_HUMAN_REVIEW"
    manifest["source_provenance"] = {
        "muse_task_ids": [p["task_id"] for p in progress["parts"]],
        "real_end_frame_bridge_count": SEGMENTS - 1,
        "source_clips_count": SEGMENTS, "source_clip_seconds": SEGMENT_SECONDS,
        "not_native_35s": True,
        "portrait_adaptation": "image_blurred_background_no_stretch",
    }
    save_json(film / "manifest.json", manifest)
    package = film / "release-package"
    package.mkdir(exist_ok=True)
    save_json(package / "douyin.json", make_package(manifest, "douyin"))
    progress["status"] = manifest["status"]
    progress["final_job"] = str(film.relative_to(root))
    save_json(report, progress)
    return film


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", required=True)
    parser.add_argument("--first-frame-file", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--confirm-seven-paid", action="store_true")
    args = parser.parse_args(argv)
    try:
        film = make_35s(args.brief, args.first_frame_file, args.out,
                        confirm_seven_paid=args.confirm_seven_paid)
        print(json.dumps({"job": str(film),
                          "status": load_json(film / "manifest.json")["status"]},
                         ensure_ascii=False))
        return 0
    except (FlowError, i2v.MediaTaskError, OSError, ValueError,
            subprocess.SubprocessError) as exc:
        print("MUSE 35s STOP: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
