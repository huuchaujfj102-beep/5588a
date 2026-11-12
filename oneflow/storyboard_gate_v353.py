"""V3.5.3 storyboard / spatial continuity G3-S offline preflight.

Fail-closed metadata validation; not a visual/semantic correctness certification.
"""
import hashlib
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED = (
    "source_script_ref", "scene_id", "camera_axis", "shot_size",
    "camera_move", "transition", "lighting_contract", "action_trajectory",
    "physical_contact", "continuity_to_prior", "editing_purpose",
    "visual_description", "narrative_emotion", "original_dialogue",
)

class StoryboardGateError(ValueError):
    pass

def _verified_file(root, asset):
    if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
        raise StoryboardGateError("BLOCK: missing source asset")
    sha = asset.get("sha256")
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise StoryboardGateError("BLOCK: missing asset SHA-256")
    path = (root / asset["path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise StoryboardGateError("BLOCK: missing/outside-workspace asset")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    if h.hexdigest() != sha.lower():
        raise StoryboardGateError("BLOCK: asset SHA mismatch")

def verify_storyboard(m, root=".", expected_shot=None):
    root = Path(root).resolve()
    if not isinstance(m, dict) or m.get("storyboard_schema") != "oneflow-g3s-v3.5.3":
        raise StoryboardGateError("BLOCK: G3-S schema missing")
    shot_id = m.get("shot_id")
    if not isinstance(shot_id, str) or not re.fullmatch(r"S\d{2}-\d{2}", shot_id):
        raise StoryboardGateError("BLOCK: invalid single-shot ID")
    if expected_shot and shot_id != expected_shot:
        raise StoryboardGateError("BLOCK: requested shot does not match manifest")
    for key in REQUIRED:
        if not isinstance(m.get(key), str) or not m[key].strip():
            raise StoryboardGateError("BLOCK: missing " + key)
    if not isinstance(m.get("spatial_anchors"), list) or not m["spatial_anchors"] or any(
        not isinstance(a, str) or not a.strip() for a in m["spatial_anchors"]
    ):
        raise StoryboardGateError("BLOCK: missing unique spatial anchors")
    for key in ("script_asset", "scene_asset", "style_asset"):
        _verified_file(root, m.get(key))
    cast = m.get("cast")
    if not isinstance(cast, list):
        raise StoryboardGateError("BLOCK: cast list missing")
    if len(cast) != len(set(cast)):
        raise StoryboardGateError("BLOCK: duplicate cast ID")
    if cast:
        assets = m.get("subject_assets")
        if not isinstance(assets, list) or set(a.get("id") for a in assets if isinstance(a, dict)) != set(cast):
            raise StoryboardGateError("BLOCK: each cast member must have one matching locked portrait")
        for asset in assets:
            _verified_file(root, asset)
    else:
        if m.get("subject_assets") not in ([], None) or m.get("prop_assets") not in ([], None):
            raise StoryboardGateError("BLOCK: environment shot cannot silently add actors/props")
    props = m.get("prop_assets", [])
    if not isinstance(props, list):
        raise StoryboardGateError("BLOCK: prop assets invalid")
    for asset in props:
        _verified_file(root, asset)
    if m.get("collage") is not False or m.get("text_overlay") is not False:
        raise StoryboardGateError("BLOCK: collage or caption in frame")
    if m.get("mode") not in ("epic_live_action", "short_drama"):
        raise StoryboardGateError("BLOCK: production mode not set")
    if m["mode"] == "short_drama":
        duration = m.get("shot_duration_seconds")
        if not isinstance(duration, (int, float)) or not (1 <= duration <= 3):
            raise StoryboardGateError("BLOCK: short-drama shot must be 1-3s")
    # For epic mode, keep source-script timings; do not impose short-drama pace.
    return {"status":"G3S_METADATA_PREFLIGHT_ONLY","shot_id":shot_id,
            "visual_identity_verified":False,"script_semantics_verified":False}
