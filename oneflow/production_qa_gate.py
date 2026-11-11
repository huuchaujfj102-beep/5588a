"""Fail-closed, offline asset gate for protected cinematic projects.

This gate validates evidence metadata, not visual identity. Human approval remains
mandatory. It never makes network calls or starts billable media generation.
"""
import argparse
import hashlib
import json
from pathlib import Path

GATES = ("identity", "wardrobe", "props", "donkey", "lotus", "grounding", "optics")
MAX_MANIFEST = 128 * 1024
MAX_FILE = 30 * 1024 * 1024


class QAGateError(ValueError):
    pass


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_manifest(manifest_path, *, root="."):
    root = Path(root).resolve()
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_file() or manifest_path.stat().st_size > MAX_MANIFEST:
        raise QAGateError("BLOCKED: missing or oversized QA manifest")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != "oneflow-qa-v3":
        raise QAGateError("BLOCKED: unsupported QA schema")
    if not isinstance(doc.get("shot_id"), str) or not doc["shot_id"].strip():
        raise QAGateError("BLOCKED: shot_id missing")
    assets = doc.get("assets")
    if not isinstance(assets, list) or not assets:
        raise QAGateError("BLOCKED: no locked assets")
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("asset_id"), str):
            raise QAGateError("BLOCKED: invalid asset entry")
        rel = asset.get("path")
        expected = asset.get("sha256")
        if not isinstance(rel, str) or not isinstance(expected, str) or len(expected) != 64:
            raise QAGateError("BLOCKED: asset path/hash missing")
        p = (root / rel).resolve()
        if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size > MAX_FILE:
            raise QAGateError("BLOCKED: asset unavailable or outside workspace")
        if digest(p) != expected.lower():
            raise QAGateError("BLOCKED: locked asset SHA256 mismatch")
    for required in ("scene_id", "camera_id", "lighting_id", "palette_id", "previous_shot_state", "change_scope"):
        if not isinstance(doc.get(required), str) or not doc[required].strip():
            raise QAGateError("BLOCKED: missing " + required)
    approvals = doc.get("seven_gates")
    if not isinstance(approvals, dict):
        raise QAGateError("BLOCKED: seven-gate checklist missing")
    for name in GATES:
        if approvals.get(name) != "PASS":
            raise QAGateError("REVIEW_REQUIRED: " + name + " not PASS")
    if doc.get("p0_open", 1) != 0 or doc.get("p1_open", 1) != 0:
        raise QAGateError("REVIEW_REQUIRED: unresolved P0/P1 issues")
    if doc.get("human_approval") != "APPROVED" or not doc.get("reviewer_id") or not doc.get("reviewed_utc"):
        raise QAGateError("REVIEW_REQUIRED: traceable human approval missing")
    supplemental = None
    if doc.get("project_id") == "baxian" or any(
        str(asset.get("asset_id", "")).startswith("BX0") for asset in assets
    ):
        from .baxian_scene_gate import check_baxian_scene
        supplemental = check_baxian_scene(doc)
    return {"status": "PREFLIGHT_PASS_METADATA_ONLY", "shot_id": doc["shot_id"],
            "asset_count": len(assets), "paid_task_created": False,
            "visual_identity_verified_by_code": False,
            "supplemental": supplemental}


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline mandatory production QA preflight")
    p.add_argument("--manifest", required=True)
    p.add_argument("--root", default=".")
    args = p.parse_args(argv)
    try:
        print(json.dumps(check_manifest(args.manifest, root=args.root), ensure_ascii=False))
        return 0
    except (QAGateError, OSError, ValueError, TypeError) as error:
        print("QA_GATE_BLOCKED: " + str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
