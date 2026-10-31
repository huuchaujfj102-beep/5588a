"""Turn one checked-in story request into an auditable OneFlow production package.

This entrypoint generates script, locked asset bible and pre-production storyboard.
It does NOT run GPU video models; a separate configured --live stage is required.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from .core import create, load_json, save_json, config, FlowError
from .director import film_prompt
from .platforms import PROFILES, make_package

ALLOWED = re.compile(r"^[a-zA-Z0-9._-]+\.json$")


def validate(request):
    if not isinstance(request, dict):
        raise FlowError("Request must be a JSON object")
    if not isinstance(request.get("title"), str) or not request["title"].strip():
        raise FlowError("Missing story title")
    if not isinstance(request.get("brief"), str) or len(request["brief"]) < 4:
        raise FlowError("Missing original brief")
    if not isinstance(request.get("characters"), dict) or not request["characters"]:
        raise FlowError("Missing locked character bible")
    if not all(isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip()
               for k, v in request["characters"].items()):
        raise FlowError("Invalid character bible")
    seconds = request.get("seconds")
    if type(seconds) is not int or not 3 <= seconds <= 90:
        raise FlowError("Requested seconds outside 3-90")
    shots = request.get("shots")
    if not isinstance(shots, list) or len(shots) != (seconds + 4) // 5:
        raise FlowError("Need exactly ceil(seconds / 5) shots for current OneFlow runtime")
    if sum(shot.get("seconds", 0) for shot in shots if isinstance(shot, dict)) != seconds:
        raise FlowError("Individual shot durations must sum to film duration")
    for i, shot in enumerate(shots):
        if not isinstance(shot, dict) or type(shot.get("seconds")) is not int:
            raise FlowError("Invalid shot duration")
        if not 1 <= shot["seconds"] <= 5:
            raise FlowError("Per-shot duration cap is five seconds")
        if not all(isinstance(shot.get(k), str) and shot[k].strip() for k in
                   ("visual", "motion", "camera", "sound", "narration")):
            raise FlowError("Shot " + str(i + 1) + " missing required director fields")
    return request


def srt_timestamp(seconds):
    if type(seconds) is not int or seconds < 0:
        raise FlowError("SRT timestamp must be nonnegative integral seconds")
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"


def production_handoff(request, manifest, narration, out):
    """Generate concrete editorial assets; NEVER imply GPU or audio was rendered."""
    srt = []
    shot_cues = []
    edit_list = []
    for index, (shot, timeline) in enumerate(zip(request["shots"], narration), 1):
        start, end = timeline["start_seconds"], timeline["end_seconds"]
        srt.extend([str(index),
                    srt_timestamp(start) + " --> " + srt_timestamp(end),
                    timeline["text"].replace("\r", " ").replace("\n", " "), ""])
        shot_cues.append({
            "shot_id": timeline["shot"], "start_seconds": start,
            "end_seconds": end, "duration_seconds": end - start,
            "narration_script": shot["narration"],
            "sound_design_prompt": shot["sound"],
            "narration_audio": None, "sound_effect_audio": None,
            "status": "AUDIO_NOT_GENERATED"
        })
        edit_list.append({
            "shot_id": timeline["shot"], "start_seconds": start,
            "end_seconds": end, "duration_seconds": end - start,
            "source_video": None, "source_audio": None,
            "status": "AWAITING_RENDERED_MEDIA"
        })
    (out / "subtitles.srt").write_text("\n".join(srt), encoding="utf-8")
    save_json(out / "audio-cues.json", {
        "status": "SCRIPT_ONLY_NO_AUDIO", "voice_language": "zh-CN",
        "soundtrack_license": "NOT_VERIFIED", "shots": shot_cues
    })
    save_json(out / "edit-decision-list.json", {
        "status": "AWAITING_REAL_VIDEO", "fps": 24, "ratio": manifest["ratio"],
        "duration_seconds": request["seconds"], "shots": edit_list
    })
    drafts = {}
    # Generate offline editor drafts for all supported platforms, but never upload.
    for platform in PROFILES:
        editorial_manifest = {**manifest,
                              "brief": request["title"] + "。 " + request["brief"]}
        draft = make_package(editorial_manifest, platform)
        drafts[platform] = {
            **draft, "status": "DRAFT_NOT_PUBLISHED",
            "video_file": None, "cover_file": None,
            "account_oauth_authorized": False,
            "manual_approval_recorded": False
        }
    save_json(out / "release-drafts.json", {
        "status": "DRAFT_ONLY", "publish_automatically": False,
        "profiles": drafts, "disclaimer":
        "These are editorial text drafts; not an actual API upload or verified platform compliance."
    })
    return {
        "subtitles": "subtitles.srt",
        "audio_cues": "audio-cues.json",
        "editing_timeline": "edit-decision-list.json",
        "release_drafts": "release-drafts.json"
    }


def package(request, out_root, cfg=None):
    request = validate(request)
    cfg = cfg or config()
    duration = request["seconds"]
    path = create(request["brief"], duration, request.get("ratio", "9:16"),
                  request.get("platforms", []), out_root, cfg)
    manifest = load_json(path / "manifest.json")
    characters = request["characters"]
    bible = "\n".join(["# 人物与造型锁定手册", "",
        "以下均为本项目独立设计的童话人物，请勿新增设定之外的角色、服装、道具或标识。",
        ""]) + "\n".join("## " + k + "\n" + v + "\n" for k, v in characters.items())
    (path / "character-bible.md").write_text(bible, encoding="utf8")
    storyboard = ["# " + request["title"], "", "**时长：** " + str(duration) + "秒",
                  "**画幅：** " + manifest["ratio"], "**状态：** PLANNED（分镜，不是已生成视频）",
                  "", "## 故事简介", request["brief"], ""]
    narration = []
    timestamp = 0
    for i, (shot, draft) in enumerate(zip(request["shots"], manifest["shots"])):
        camera_details = (shot["visual"] + "\n人物动作：" + shot["motion"] +
                          "\n镜头运动：" + shot["camera"])
        previous = request["shots"][i-1]["visual"] if i else None
        text = film_prompt(request["brief"], camera_details, previous,
                           i + 1, len(request["shots"]))
        # Keep character identity lock in every prompt and avoid style drift.
        text += "\n\n全片人物和服装唯一设定（不得改变）：\n" + (
            "; ".join(k + ": " + v for k, v in characters.items()))
        draft["visual_prompt"] = text
        draft["narrative_phase"] = shot["visual"]
        draft["audio_prompt"] = shot["sound"]
        draft["narration"] = shot["narration"]
        draft["camera"] = shot["camera"]
        draft["motion"] = shot["motion"]
        draft["seconds"] = shot["seconds"]
        storyboard += ["### " + draft["id"] + " (" + str(shot["seconds"]) + "s)",
                       "**画面：** " + shot["visual"], "**动作：** " + shot["motion"],
                       "**镜头：** " + shot["camera"], "**音效：** " + shot["sound"],
                       "**旁白：** " + shot["narration"], ""]
        narration.append({"shot": draft["id"], "start_seconds": timestamp,
                          "end_seconds": timestamp + shot["seconds"],
                          "text": shot["narration"]})
        timestamp += shot["seconds"]
    manifest["offline_handoff"] = production_handoff(request, manifest, narration, path)
    manifest["title"] = request["title"]
    manifest["character_bible"] = "character-bible.md"
    manifest["original_story_type"] = "Grimm fairy-tale inspired original adaptation"
    manifest["narration_timing"] = "narration.json"
    manifest["warnings"].append("Narration text is not synthesized into an audio file yet.")
    manifest["warnings"].append("Subtitles, audio-cue timeline and social-release metadata are drafts, not rendered, audited or uploaded assets.")
    manifest["warnings"].append("No image/video/audio model was called at request-package stage.")
    save_json(path / "manifest.json", manifest)
    save_json(path / "narration.json", narration)
    (path / "storyboard.md").write_text("\n".join(storyboard), encoding="utf8")
    (path / "rendering-checklist.md").write_text(
        "# 生成与审核验收\n\n"
        "- [ ] 为白雪公主、王后及七位小矮人建立正式参考图并人工批准\n"
        "- [ ] 按 S01-S12 顺序出图；每次只改变本镜头动作\n"
        "- [ ] 图生视频，检查角色衣物、人物数量、时空光线与镜头连贯\n"
        "- [ ] 生成旁白与原创配乐、音效，剪辑同步到60秒\n"
        "- [ ] 真实 MP4 通过 FFprobe、视觉审核和版权审核\n"
        "- [ ] 用户亲自审核成片；未审批不得发布\n",
        encoding="utf8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path)
    parser.add_argument("--out", type=Path, default=Path("oneflow-preview"))
    args = parser.parse_args(argv)
    try:
        src = args.request
        if src.parent.as_posix() != "oneflow/requests" or not ALLOWED.fullmatch(src.name):
            raise FlowError("Story request must be a oneflow/requests/*.json repository path")
        if not src.is_file() or src.stat().st_size > 150_000:
            raise FlowError("Missing or oversized story request")
        task = json.loads(src.read_text(encoding="utf8"))
        folder = package(task, args.out)
        print(json.dumps({"job": str(folder), "status": "PLANNED",
                          "shot_count": len(task["shots"]),
                          "media_generated": False}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, FlowError) as exc:
        print("STORY REQUEST ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
