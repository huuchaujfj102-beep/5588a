"""Create five-platform handoff metadata from ONE completed, audited MP4.

No platform API requests are made here. A release package is NOT a post.
"""
import argparse
import json
from pathlib import Path

from .core import FlowError, digest, load_json, save_json
from .platforms import make_package

TARGETS = ("douyin", "kuaishou", "xiaohongshu", "shipinhao", "youtube")


def build_delivery_kit(job):
    root = Path(job).resolve()
    manifest_path = root / "manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != "AWAITING_HUMAN_REVIEW":
        raise FlowError("A real audited MP4 awaiting human review is required")
    if manifest.get("approval") is not None:
        raise FlowError("Use the independent approved publisher for an already approved job")
    render = manifest.get("render")
    if not isinstance(render, str) or not render or Path(render).is_absolute():
        raise FlowError("Missing or unsafe render path")
    clip = (root / render).resolve()
    if not clip.is_relative_to(root) or clip.suffix.lower() != ".mp4" or not clip.is_file():
        raise FlowError("Missing reviewed MP4")
    if clip.stat().st_size < 256:
        raise FlowError("Reviewed MP4 is too small")
    qc = load_json(root / "qc.json")
    checksum = digest(clip)
    if qc.get("status") != "REVIEW_REQUIRED" or qc.get("video_sha256") != checksum:
        raise FlowError("QC was not passed to the human review stage or the MP4 hash changed")
    if not set(TARGETS).issubset(set(manifest.get("platforms", []))):
        raise FlowError("Five target platforms must be specified at generation time")
    delivery = root / "delivery-kit"
    delivery.mkdir(exist_ok=True)
    records = []
    for platform in TARGETS:
        pkg = make_package(manifest, platform)
        pkg.update({
            "source_video": render,
            "video_sha256": checksum,
            "human_review_status": "PENDING",
            "publisher_authorization_status": "NOT_VERIFIED",
            "publication_status": "NOT_SUBMITTED",
            "official_post_id": None,
            "official_post_url": None,
            "published_at": None,
            "instructions": (
                "Confirm visual quality, rights, aspect ratio and official platform permissions. "
                "Submit using the platform's authorized publisher or approved human handoff; "
                "record the official receipt independently."
            ),
        })
        save_json(delivery / (platform + ".json"), pkg)
        records.append({"platform": platform, "status": "NOT_SUBMITTED",
                        "package": "delivery-kit/" + platform + ".json"})
    report = {
        "schema": "oneflow-five-platform-handoff-v1",
        "production_status": "AWAITING_HUMAN_REVIEW",
        "published_count": 0,
        "targets": records,
        "video_sha256": checksum,
        "video_path": render,
        "notice": "No OAuth called. No publication attempted or claimed.",
    }
    save_json(delivery / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate verified five-platform editorial handoff")
    parser.add_argument("--jobs-root", required=True)
    args = parser.parse_args(argv)
    try:
        directory = Path(args.jobs_root)
        jobs = list(directory.glob("film-*/manifest.json"))
        if len(jobs) != 1:
            raise FlowError("Expected exactly one completed film job")
        print(json.dumps(build_delivery_kit(jobs[0].parent), ensure_ascii=False))
        return 0
    except (FlowError, OSError, ValueError, KeyError) as exc:
        print("DISTRIBUTION ERROR: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
