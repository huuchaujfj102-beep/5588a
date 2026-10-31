"""Unified one-sentence film production: plan -> render -> audit -> approval -> publish -> metrics.

Secure-by-default: plan is offline; rendering needs explicitly configured live providers;
publishing requires both human attestation and an authorized publisher service.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from .providers import ProviderError, exchange, generate, json_call, ollama_shots, endpoint
from .router import RoutingError, route, preflight
from .director import film_prompt, phase_list


class FlowError(RuntimeError):
    pass


PLATFORMS = ("douyin", "kuaishou", "xiaohongshu", "bilibili", "youtube", "tiktok")
DEFAULT = {
    "story": {"kind": "heuristic"},
    "image": [],
    "video": [],
    "audio": [],
    "require_audio": True,
    "audio_mode": "separate",
    "commercial": True,
    "frame_bridge": False,
    "max_shots": 12,
    "resolution": [1080, 1920],
    "fps": 24,
    "publisher": {}
}
MANUAL_GATES = [
    "identity_and_reference_continuity", "shot_to_shot_physics",
    "lip_sync_and_sound_fidelity", "rights_and_music_licenses",
    "platform_compliance", "final_human_signoff"
]


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def config(path=None):
    if not path:
        return dict(DEFAULT)
    src = load_json(path)
    if not isinstance(src, dict):
        raise FlowError("Config must be a JSON object")
    return {**DEFAULT, **src}


def describe(prompt, seconds, count, cfg):
    story = cfg.get("story", {})
    if story.get("kind") == "ollama":
        drafts = ollama_shots(story, prompt, seconds, count)
        planner = "ollama_live"
    elif story.get("kind") == "heuristic":
        phases = phase_list(prompt)
        drafts = [
            {"prompt": phases[min(len(phases) - 1, i * len(phases) // count)],
             "sound": "Original location effects for this action; no narration unless explicitly requested."}
            for i in range(count)
        ]
        planner = "heuristic_draft_not_ai_storyboard"
    else:
        raise FlowError("Unknown story planning provider")
    output = []
    for i, draft in enumerate(drafts):
        if not isinstance(draft, dict) or not draft.get("prompt") or not draft.get("sound"):
            raise FlowError("Storyboard missing visual or audio prompt")
        previous = drafts[i-1]["prompt"] if i else None
        output.append({
            "prompt": film_prompt(prompt, draft["prompt"], previous, i + 1, count),
            "sound": draft["sound"],
            "phase": draft["prompt"]
        })
    return output, planner


def create(prompt, seconds, ratio, platforms, out_root, cfg):
    if not isinstance(prompt, str) or len(prompt.strip()) < 4 or len(prompt) > 6000:
        raise FlowError("Prompt needs 4-6000 characters")
    seconds = int(seconds)
    if not 3 <= seconds <= 90:
        raise FlowError("Duration must be 3-90 seconds")
    if ratio not in ("9:16", "16:9", "1:1"):
        raise FlowError("Unsupported aspect ratio")
    unknown = set(platforms) - set(PLATFORMS)
    if unknown:
        raise FlowError("Unsupported platforms: " + ",".join(sorted(unknown)))
    shots_count = max(1, (seconds + 4) // 5)
    if shots_count > int(cfg["max_shots"]):
        raise FlowError("Shot count exceeds configured cost cap")
    storyboard, planner = describe(prompt, seconds, shots_count, cfg)
    if len(storyboard) != shots_count:
        raise FlowError("Story planner did not return the required shot count")
    durations = [seconds // shots_count] * shots_count
    for i in range(seconds % shots_count):
        durations[i] += 1
    ident = "film-" + uuid.uuid4().hex[:12]
    root = Path(out_root).resolve() / ident
    root.mkdir(parents=True, exist_ok=False)
    shots = []
    for i, item in enumerate(storyboard):
        shots.append({
            "id": "S" + str(i + 1).zfill(2),
            "seconds": durations[i],
            "visual_prompt": item["prompt"],
            "audio_prompt": item["sound"],
            "narrative_phase": item["phase"],
            "image": None, "video": None, "audio": None,
            "model_provenance": {},
            "normalized": None, "state": "PLANNED"
        })
    manifest = {
        "schema": "oneflow.v1", "id": ident, "created_at": now(),
        "brief": prompt, "seconds": seconds, "ratio": ratio,
        "planner": planner, "commercial": cfg.get("commercial", True),
        "platforms": sorted(set(platforms)),
        "status": "PLANNED", "shots": shots, "render": None, "qc": None,
        "approval": None, "publication": {}, "metrics": {},
        "warnings": ["Story draft is not a substitute for visual review.",
                     "Generation, licensing and publishing are not activated by plan creation."]
    }
    save_json(root / "manifest.json", manifest)
    outline = ["# " + ident, "", "Original brief: " + prompt, "",
               "Planner: " + planner, ""]
    for shot in shots:
        outline += ["## " + shot["id"] + " (" + str(shot["seconds"]) + " s)",
                    shot["visual_prompt"], "", "Sound: " + shot["audio_prompt"], ""]
    (root / "storyboard.md").write_text("\n".join(outline), encoding="utf-8")
    return root


def job_root(job):
    root = Path(job).resolve()
    if root.is_file():
        root = root.parent
    if not (root / "manifest.json").exists():
        raise FlowError("Job manifest not found")
    return root


def digest(path):
    hashv = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hashv.update(chunk)
    return hashv.hexdigest()


def command(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, check=True, text=True,
                                capture_output=True, timeout=1800)
        return result.stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise FlowError("Media command failed: " + type(exc).__name__) from None


def probe(path):
    raw = command(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                   "-of", "json", str(path)])
    return json.loads(raw)


def primary_media(info, codec_type):
    return next((item for item in info.get("streams", [])
                 if item.get("codec_type") == codec_type), None)


def normalize(root, shot, fps, width, height, require_audio):
    clip = root / shot["video"]
    info = probe(clip)
    if not primary_media(info, "video"):
        raise FlowError(shot["id"] + " has no video stream")
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration < shot["seconds"] - 0.4:
        raise FlowError(shot["id"] + " too short; do not silently freeze or duplicate frames")
    embedded_audio = bool(primary_media(info, "audio"))
    if require_audio and not shot["audio"] and not embedded_audio:
        raise FlowError(shot["id"] + " has no sound effects")
    output = root / "media" / (shot["id"] + "-normalized.mp4")
    aspect = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p"
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(clip)]
    if shot["audio"]:
        args += ["-i", str(root / shot["audio"])]
        audio_map = "1:a:0"
    elif embedded_audio:
        audio_map = "0:a:0"
    else:
        args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        audio_map = "1:a:0"
    args += ["-map", "0:v:0", "-map", audio_map, "-vf", aspect,
             "-af", "aresample=48000,apad",
             "-t", str(shot["seconds"]), "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
             "-r", str(fps), "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", str(output)]
    command(args)
    return str(output.relative_to(root))


def assemble(root, manifest, cfg):
    fps = int(cfg.get("fps", 24))
    if fps < 12 or fps > 60:
        raise FlowError("Invalid FPS")
    ratio = manifest["ratio"]
    width, height = {"9:16": (1080, 1920), "16:9": (1920, 1080),
                     "1:1": (1080, 1080)}[ratio]
    for shot in manifest["shots"]:
        shot["normalized"] = normalize(root, shot, fps, width, height,
                                        cfg.get("require_audio", True))
    playlist = root / "media" / "concat.txt"
    playlist.write_text("".join("file '" + Path(s["normalized"]).name +
                                "'\n" for s in manifest["shots"]), encoding="utf-8")
    dest = root / "final-draft.mp4"
    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "concat", "-safe", "1", "-i", "concat.txt",
             "-c", "copy", "-movflags", "+faststart", str(dest)], cwd=root / "media")
    return dest


def assets(root, manifest):
    path = root / "assets.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["asset_id", "source", "license", "proof", "usage_scope"])
        for shot in manifest["shots"]:
            for stage in ("image", "video", "audio"):
                if shot[stage]:
                    writer.writerow([shot["id"] + "-" + stage,
                                     shot[stage], "UNVERIFIED",
                                     "REVIEW_REQUIRED", "PENDING_REVIEW"])
    return path


def audit(root, manifest, cfg, media):
    from film_audit.audit import check_assets, check_video
    import csv
    ledger = assets(root, manifest)
    issues = check_assets(ledger)
    issues += check_video(media, {"min_short_side": 1080,
                                 "min_duration": manifest["seconds"] - 1,
                                 "max_duration": manifest["seconds"] + 1})
    info = probe(media)
    length = float(info.get("format", {}).get("duration") or 0)
    if abs(length - manifest["seconds"]) > 1.0:
        issues.append({"module": "media_spec", "severity": "blocker",
                       "code": "DURATION_MISMATCH", "message": "Final duration differs from brief"})
    if cfg.get("require_audio", True) and not primary_media(info, "audio"):
        issues.append({"module": "audio", "severity": "blocker",
                       "code": "MISSING_REQUIRED_SOUND", "message": "Audio stage incomplete"})
    qc = {"status": "FAIL" if any(x.get("severity") == "blocker" for x in issues)
          else "REVIEW_REQUIRED",
          "video_sha256": digest(media), "checked_at": now(),
          "automated_checks": ["existing_film_audit.asset_ledger", "existing_film_audit.ffprobe",
                               "duration_and_audio_presence"],
          "issues": issues, "manual_review_required": MANUAL_GATES,
          "notice": "Technical checks DO NOT verify physical logic, image consistency, actual sound fidelity or licenses."}
    save_json(root / "qc.json", qc)
    return qc


def produce(job, cfg):
    root = job_root(job)
    manifest = load_json(root / "manifest.json")
    if manifest["approval"] is not None:
        raise FlowError("Approved jobs cannot be modified; create a new version")
    if not cfg.get("image") or not cfg.get("video"):
        raise FlowError("Configure real image and video models before rendering")
    if cfg.get("require_audio", True) and cfg.get("audio_mode", "separate") == "separate" and not cfg.get("audio"):
        raise FlowError("Configured sound generation required; no fake or silent substitution")
    preflight(cfg)
    routed = {stage: route(stage, cfg.get(stage, []), commercial=cfg.get("commercial", True))
              for stage in ("image", "video", "audio")}
    if bool(manifest.get("commercial", True)) != bool(cfg.get("commercial", True)):
        raise FlowError("Commercial-use flag changed since project creation")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise FlowError("FFmpeg and FFprobe are required")
    media_dir = root / "media"
    media_dir.mkdir(exist_ok=True)
    manifest["status"] = "RENDERING"
    save_json(root / "manifest.json", manifest)
    try:
        previous = None
        for shot in manifest["shots"]:
            values = {"prompt": shot["visual_prompt"], "negative_prompt":
                      "identity drift, continuity errors, extra characters, physical impossibilities, watermark",
                      "seconds": shot["seconds"],
                      "seed": int(hashlib.sha256((manifest["id"] + shot["id"]).encode()).hexdigest()[:8], 16),
                      "image": None}
            if cfg.get("frame_bridge", False) and previous:
                tail = media_dir / (previous["id"] + "-tail.png")
                if not tail.exists():
                    command(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                             "-sseof", "-0.2", "-i", str(root / previous["video"]),
                             "-frames:v", "1", str(tail)])
                values["reference_image"] = str(tail)
            if not shot["image"] or not (root / shot["image"]).exists():
                image_path, model_id = generate("image", routed["image"], values,
                                      media_dir / (shot["id"] + "-image"), return_used=True)
                shot["image"] = str(image_path.relative_to(root))
                shot.setdefault("model_provenance", {})["image"] = model_id
                shot["state"] = "IMAGE_GENERATED_UNREVIEWED"
                save_json(root / "manifest.json", manifest)
            values["image"] = str(root / shot["image"])
            if not shot["video"] or not (root / shot["video"]).exists():
                video_path, model_id = generate("video", routed["video"], values,
                                      media_dir / (shot["id"] + "-video"), return_used=True)
                shot["video"] = str(video_path.relative_to(root))
                shot.setdefault("model_provenance", {})["video"] = model_id
                shot["state"] = "VIDEO_GENERATED_UNREVIEWED"
                save_json(root / "manifest.json", manifest)
            if cfg.get("audio_mode", "separate") == "embedded":
                if not primary_media(probe(root / shot["video"]), "audio"):
                    raise FlowError("Selected audio-video model did not produce an audio track")
                shot["state"] = "EMBEDDED_AUDIO_UNREVIEWED"
                save_json(root / "manifest.json", manifest)
            if cfg.get("audio_mode", "separate") == "separate" and routed["audio"] and (not shot["audio"] or not (root / shot["audio"]).exists()):
                sound_values = {**values, "prompt": shot["audio_prompt"]}
                sound_path, model_id = generate("audio", routed["audio"], sound_values,
                                      media_dir / (shot["id"] + "-sound"), return_used=True)
                shot["audio"] = str(sound_path.relative_to(root))
                shot.setdefault("model_provenance", {})["audio"] = model_id
                shot["state"] = "MEDIA_GENERATED_UNREVIEWED"
                save_json(root / "manifest.json", manifest)
            previous = shot
        video = assemble(root, manifest, cfg)
        manifest["render"] = str(video.relative_to(root))
        qc = audit(root, manifest, cfg, video)
        manifest["qc"] = "qc.json"
        manifest["status"] = "BLOCKED" if qc["status"] == "FAIL" else "AWAITING_HUMAN_REVIEW"
        save_json(root / "manifest.json", manifest)
        return manifest["status"]
    except (FlowError, ProviderError, RoutingError, OSError, ValueError) as exc:
        manifest["status"] = "FAILED"
        manifest["error"] = str(exc)
        save_json(root / "manifest.json", manifest)
        raise


def approve(job, reviewer, visual_attested=False, rights_attested=False):
    root = job_root(job)
    manifest = load_json(root / "manifest.json")
    if manifest["status"] != "AWAITING_HUMAN_REVIEW":
        raise FlowError("Only an audited, unblocked draft can be approved")
    if not reviewer.strip() or not visual_attested or not rights_attested:
        raise FlowError("Named human review, visual and rights attestations are mandatory")
    qc = load_json(root / "qc.json")
    media = root / manifest["render"]
    if qc["status"] != "REVIEW_REQUIRED" or digest(media) != qc["video_sha256"]:
        raise FlowError("QC failed or video changed since audit")
    manifest["approval"] = {"reviewer": reviewer, "approved_at": now(),
                            "video_sha256": digest(media), "visual_attested": True,
                            "rights_attested": True}
    manifest["status"] = "APPROVED"
    save_json(root / "manifest.json", manifest)
    return manifest


def authorize_publish(root, manifest, platform):
    if platform not in PLATFORMS or platform not in manifest["platforms"]:
        raise FlowError("Platform must be explicitly selected in the original job")
    if manifest["status"] not in ("APPROVED", "PARTIALLY_PUBLISHED", "PUBLISHED"):
        raise FlowError("Cannot publish without human approval")
    if not manifest["approval"]:
        raise FlowError("Missing human approval")
    if manifest["approval"]["video_sha256"] != digest(root / manifest["render"]):
        raise FlowError("Video changed since approval")
    if manifest["approval"]["video_sha256"] != load_json(root / "qc.json")["video_sha256"]:
        raise FlowError("Approval/QC digest mismatch")


def publish(job, platform, cfg, consent=False):
    root = job_root(job)
    manifest = load_json(root / "manifest.json")
    authorize_publish(root, manifest, platform)
    if not consent:
        raise FlowError("Per-platform explicit publication consent is required")
    existing = manifest["publication"].get(platform)
    if existing and existing.get("status") == "published":
        return existing
    pub_cfg = cfg.get("publisher", {})
    if not pub_cfg.get("url_env") and not pub_cfg.get("url"):
        raise FlowError("Publisher is not connected; export package only")
    base = endpoint(pub_cfg)
    video = (root / manifest["render"]).read_bytes()
    if len(video) > 500_000_000:
        raise FlowError("Video too large for basic publisher bridge; use chunked uploader")
    boundary = "oneflow" + uuid.uuid4().hex
    meta = {"job_id": manifest["id"], "platform": platform,
            "title": manifest["brief"][:100],
            "description": manifest["brief"][:2000],
            "sha256": manifest["approval"]["video_sha256"],
            "idempotency_key": manifest["id"] + "-" + platform}
    prefix = ('--' + boundary + '\r\nContent-Disposition: form-data; name="metadata"\r\n' +
              'Content-Type: application/json\r\n\r\n').encode()
    center = ('\r\n--' + boundary + '\r\nContent-Disposition: form-data; ' +
              'name="video"; filename="final.mp4"\r\nContent-Type: video/mp4\r\n\r\n').encode()
    payload = prefix + json.dumps(meta, ensure_ascii=False).encode("utf-8") + center + video + (
        '\r\n--' + boundary + '--\r\n').encode()
    raw = exchange(base + "/publish", pub_cfg, payload, method="POST",
                   content_type="multipart/form-data; boundary=" + boundary, timeout=600)
    try:
        response = json.loads(raw)
        state = response.get("status")
        external_id = response.get("id")
        if state not in ("published", "pending") or not external_id:
            raise ValueError()
    except (ValueError, AttributeError):
        raise FlowError("Publisher response has no verifiable publication ID/status") from None
    record = {"status": state, "external_id": str(external_id), "url": response.get("url"),
              "updated_at": now()}
    manifest["publication"][platform] = record
    count = sum(x["status"] == "published" for x in manifest["publication"].values())
    manifest["status"] = "PUBLISHED" if count == len(manifest["platforms"]) else "PARTIALLY_PUBLISHED"
    save_json(root / "manifest.json", manifest)
    return record


def metrics(job, cfg):
    root = job_root(job)
    manifest = load_json(root / "manifest.json")
    pub_cfg = cfg.get("publisher", {})
    base = endpoint(pub_cfg)
    for platform, record in manifest["publication"].items():
        if record["status"] != "published":
            continue
        query = urlencode({"platform": platform, "id": record["external_id"]})
        result = json_call(base + "/metrics?" + query, pub_cfg)
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise FlowError("Invalid metrics for " + platform)
        manifest["metrics"][platform] = {"data": result.get("data", {}),
                                          "collected_at": now()}
    save_json(root / "manifest.json", manifest)
    return manifest["metrics"]


def main(argv=None):
    p = argparse.ArgumentParser(description="One sentence -> production -> audit -> human approval -> publish -> metrics")
    sub = p.add_subparsers(dest="action", required=True)
    start = sub.add_parser("run", help="Plan a one-sentence film, optionally render live")
    start.add_argument("--prompt", required=True)
    start.add_argument("--seconds", type=int, default=35)
    start.add_argument("--ratio", default="9:16")
    start.add_argument("--platform", action="append", default=[])
    start.add_argument("--out", default="private-inputs/oneflow-jobs")
    start.add_argument("--config")
    start.add_argument("--live", action="store_true", help="Explicitly use paid/compute-intensive live model endpoints")
    for cmd in ("produce", "approve", "publish", "metrics", "status"):
        child = sub.add_parser(cmd)
        child.add_argument("--job", required=True)
        if cmd in ("produce", "publish", "metrics"):
            child.add_argument("--config")
        if cmd == "approve":
            child.add_argument("--reviewer", required=True)
            child.add_argument("--visual-attested", action="store_true")
            child.add_argument("--rights-attested", action="store_true")
        if cmd == "publish":
            child.add_argument("--platform", required=True, choices=PLATFORMS)
            child.add_argument("--consent", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.action == "run":
            cfg = config(args.config)
            job = create(args.prompt, args.seconds, args.ratio, args.platform, args.out, cfg)
            if args.live:
                produce(job, cfg)
            print(json.dumps({"job": str(job), "status": load_json(job / "manifest.json")["status"]},
                             ensure_ascii=False))
        elif args.action == "produce":
            print(produce(args.job, config(args.config)))
        elif args.action == "approve":
            result = approve(args.job, args.reviewer, args.visual_attested, args.rights_attested)
            print(result["status"])
        elif args.action == "publish":
            print(json.dumps(publish(args.job, args.platform, config(args.config), args.consent),
                             ensure_ascii=False))
        elif args.action == "metrics":
            print(json.dumps(metrics(args.job, config(args.config)), ensure_ascii=False))
        else:
            root = job_root(args.job)
            data = load_json(root / "manifest.json")
            print(json.dumps({"id": data["id"], "status": data["status"],
                              "shots": len(data["shots"]), "published": data["publication"]},
                             ensure_ascii=False))
        return 0
    except (FlowError, ProviderError, RoutingError, OSError, ValueError) as exc:
        print("ONEFLOW ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
