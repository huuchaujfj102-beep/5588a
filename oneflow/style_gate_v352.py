"""V3.5.2 ancient live-action style gate: offline, fail closed.

This validates files and review *records*. It cannot prove a model actually used
a reference image, nor can it judge pixels. The calling adapter must provide
an image-conditioned path; text-only generation must not claim style locking.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

STYLE_ID = "STYLE_MASTER_LIVE_ACTION_ANCIENT_COAST_V1"
SCHEMA = "oneflow-style-v3.5.2"
G4_CHECKS = ("identity", "wardrobe", "props", "animal", "platform",
             "contact", "optics", "realism", "scene", "physics", "single_shot")
HEX64 = re.compile(r"^[a-fA-F0-9]{64}$")


class StyleGateError(ValueError):
    pass


def _file(root, rel, expected):
    if not isinstance(rel, str) or not rel.strip() or not isinstance(expected, str) or not HEX64.fullmatch(expected):
        raise StyleGateError("BLOCK: missing local path or sha256")
    root = Path(root).resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise StyleGateError("BLOCK: unbound or inaccessible reference asset")
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    if h.hexdigest() != expected.lower():
        raise StyleGateError("BLOCK: style/first-frame sha256 mismatch")
    return p


def verify(manifest_path, root=".", stage="image"):
    if stage not in ("image", "video"):
        raise StyleGateError("BLOCK: unsupported stage")
    p = Path(manifest_path)
    if not p.is_file() or p.stat().st_size > 100_000:
        raise StyleGateError("BLOCK: missing or oversized manifest")
    m = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(m, dict) or m.get("schema") != SCHEMA or m.get("style_id") != STYLE_ID:
        raise StyleGateError("BLOCK: style contract/schema mismatch")
    for key in ("shot_id", "scene_id", "lighting_contract", "weather_contract",
                "material_contract", "color_profile", "scene_anchor", "camera_composition"):
        if not isinstance(m.get(key), str) or not m[key].strip():
            raise StyleGateError("BLOCK: missing " + key)
    _file(root, m.get("style_source_path"), m.get("style_source_sha256"))
    if not isinstance(m.get("reference_binding_evidence"), str) or not m["reference_binding_evidence"].strip():
        raise StyleGateError("BLOCK: no record of actual reference binding")
    if m.get("reference_method") not in ("verified_image_input", "original_pixel_composite"):
        raise StyleGateError("BLOCK: no image-conditioned reference route")
    if m.get("collage") is not False or m.get("text_overlay") is not False:
        raise StyleGateError("BLOCK: collage or typography not prohibited")
    if stage == "video":
        _file(root, m.get("approved_first_frame_path"), m.get("approved_first_frame_sha256"))
        if m.get("g4_status") != "G4_PASS_HUMAN" or m.get("human_approval") != "APPROVED":
            raise StyleGateError("BLOCK: no G4 human approval of first frame")
        if not isinstance(m.get("reviewer"), str) or not m["reviewer"].strip():
            raise StyleGateError("BLOCK: no reviewer")
        checks = m.get("g4_checks")
        if not isinstance(checks, dict) or any(checks.get(x) != "PASS" for x in G4_CHECKS):
            raise StyleGateError("BLOCK: G4 checks incomplete")
        camera = m.get("camera_motion")
        if not isinstance(camera, str) or not camera.strip():
            raise StyleGateError("BLOCK: missing camera motion")
    return {"status": "PREFLIGHT_METADATA_PASS_ONLY", "stage": stage,
            "shot_id": m["shot_id"], "visual_review_done_by_code": False,
            "reference_consumption_proven_by_code": False}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--stage", choices=("image", "video"), required=True)
    a = ap.parse_args(argv)
    try:
        print(json.dumps(verify(a.manifest, a.root, a.stage), ensure_ascii=False))
        return 0
    except (StyleGateError, OSError, ValueError, TypeError) as exc:
        print("STYLE_GATE_BLOCKED: " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
