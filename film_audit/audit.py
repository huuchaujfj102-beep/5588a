import argparse
import csv
import json
import re
import subprocess
from pathlib import Path

REQUIRED = {"asset_id", "source", "license", "proof", "usage_scope"}
GATES = ["story_prompt", "content_compliance_copyright", "cast_continuity",
         "visual_physics", "lipsync_audio_subtitles", "ocr_watermark_media",
         "final_review"]

def flag(module, severity, code, message, **extra):
    return dict(module=module, severity=severity, code=code, message=message, **extra)

def ms(value):
    m = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", value.strip())
    if not m:
        raise ValueError("Invalid SRT timestamp")
    h, minute, sec, milli = map(int, m.groups())
    if minute > 59 or sec > 59:
        raise ValueError("Invalid SRT timestamp")
    return ((h * 60 + minute) * 60 + sec) * 1000 + milli

def check_srt(path):
    if not path.exists():
        return [flag("audio_subtitles", "blocker", "MISSING_SRT", str(path))]
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return [flag("audio_subtitles", "blocker", "EMPTY_SRT", "字幕为空")]
    issues, prev = [], 0
    for i, block in enumerate(re.split(r"\n\s*\n", text), 1):
        line = next((v for v in block.splitlines() if " --> " in v), None)
        if not line:
            issues.append(flag("audio_subtitles", "blocker", "NO_TIMING", "缺少时间码", block=i))
            continue
        try:
            start, end = [ms(p) for p in line.split(" --> ")]
        except ValueError:
            issues.append(flag("audio_subtitles", "blocker", "INVALID_TIMING", "错误时间码", block=i))
            continue
        if end <= start:
            issues.append(flag("audio_subtitles", "blocker", "NEGATIVE_DURATION", "时长无效", block=i))
        if start < prev:
            issues.append(flag("audio_subtitles", "warning", "OVERLAP", "字幕重叠", block=i))
        prev = max(prev, end)
    return issues

def check_assets(path):
    if not path.exists():
        return [flag("copyright", "blocker", "MISSING_LEDGER", "缺少素材授权登记")]
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = csv.DictReader(f)
        if not REQUIRED.issubset(rows.fieldnames or []):
            return [flag("copyright", "blocker", "BAD_COLUMNS", "台账字段不齐")]
        return [flag("copyright", "blocker", "MISSING_LICENSE", "授权信息缺失", row=i)
                for i, row in enumerate(rows, 2)
                if any(not (row.get(k) or "").strip() for k in REQUIRED)]

def check_video(path, cfg):
    if not path.exists():
        return [flag("media_spec", "blocker", "MISSING_VIDEO", "视频不存在")]
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                            "-of", "json", str(path)], capture_output=True,
                           text=True, timeout=40, check=True)
        data = json.loads(r.stdout)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return [flag("media_spec", "blocker", "FFPROBE_FAILED", "媒体读取失败/缺少 ffprobe")]
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        return [flag("media_spec", "blocker", "NO_VIDEO_STREAM", "未发现视频流")]
    result = []
    if min(int(v.get("width", 0)), int(v.get("height", 0))) < cfg.get("min_short_side", 1080):
        result.append(flag("media_spec", "warning", "LOW_RESOLUTION", "短边分辨率不足"))
    if not any(s.get("codec_type") == "audio" for s in data.get("streams", [])):
        result.append(flag("media_spec", "warning", "NO_AUDIO", "没有音轨"))
    duration = float(data.get("format", {}).get("duration") or 0)
    if not cfg.get("min_duration", 0) <= duration <= cfg.get("max_duration", 999999):
        result.append(flag("media_spec", "warning", "DURATION", "视频时长不符"))
    return result

def main():
    p = argparse.ArgumentParser()
    for k in ("video", "srt", "assets", "config", "output"):
        p.add_argument("--" + k, type=Path)
    args = p.parse_args()
    config_path = args.config or Path("audit-config.json")
    cfg = json.loads(config_path.read_text(encoding="utf8")) if config_path.exists() else {}
    issues = []
    if args.video:
        issues += check_video(args.video, cfg)
    if args.srt:
        issues += check_srt(args.srt)
    issues += check_assets(args.assets or Path("assets.csv"))
    result = {
      "status": "FAIL" if any(x["severity"] == "blocker" for x in issues) else "REVIEW_REQUIRED",
      "automated_checks": ["asset_ledger"] + (["srt_timing"] if args.srt else []) + (["ffprobe"] if args.video else []),
      "manual_review_required": GATES,
      "issues": issues,
      "disclaimer": "自动技术检测不能证明人物一致性、口型、隐水印或版权合法性"
    }
    output = args.output or Path("audit-report.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result["status"] == "FAIL")

if __name__ == "__main__":
    raise SystemExit(main())
