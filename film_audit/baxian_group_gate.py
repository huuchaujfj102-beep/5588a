"""Fail-closed source/layer metadata gate for Eight Immortals group shots.

This is NOT computer vision. It verifies declared references, hashes, layers,
masks, cast/prop mappings, blocking and human-review evidence. Face fidelity,
anatomy, water physics and artistic judgment still require actual image review.
No source images or layers are uploaded by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _safe_path(root: Path, name: str, issues: list, code: str) -> Path | None:
    if not isinstance(name, str) or not name.strip():
        issues.append({"code": code, "message": "Missing file path"})
        return None
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        issues.append({"code": "PATH_ESCAPE", "message": "Path escapes asset root"})
        return None
    if not path.is_file():
        issues.append({"code": code, "message": "File not found", "file": name})
        return None
    return path


def _match_hash(root: Path, name: str, expected: str | None,
                issues: list, label: str) -> Path | None:
    path = _safe_path(root, name, issues, "MISSING_ASSET")
    if path is None:
        return None
    if not isinstance(expected, str) or len(expected) != 64:
        issues.append({"code": "MISSING_HASH", "message": label})
        return None
    if _sha256(path) != expected.lower():
        issues.append({"code": "HASH_MISMATCH", "message": label, "file": name})
        return None
    return path


def _png_info(path: Path, issues: list, label: str) -> tuple | None:
    try:
        with path.open("rb") as stream:
            header = stream.read(33)
        if (len(header) != 33 or header[:8] != b"\x89PNG\r\n\x1a\n"
                or header[12:16] != b"IHDR"):
            raise ValueError("not a valid PNG header")
        width, height, depth, color = struct.unpack(">IIBB", header[16:26])
        if width < 1 or height < 1 or depth not in (1, 2, 4, 8, 16):
            raise ValueError("invalid PNG dimensions or bit depth")
        return width, height, color
    except (OSError, ValueError, struct.error):
        issues.append({"code": "BAD_PNG", "message": label})
        return None


def validate(plan: dict, authority: dict, policy: dict, root: Path,
             phase: str) -> dict:
    """Returns factual gate result. Does not assert human image checks passed."""
    errors, pending = [], []
    if not isinstance(plan, dict) or not isinstance(authority, dict) or not isinstance(policy, dict):
        return {"status": "BLOCKED", "issues": [{"code": "BAD_MANIFEST"}]}

    if plan.get("schema_version") != 3:
        errors.append({"code": "INVALID_SCHEMA"})
    if plan.get("mode") != policy.get("production_mode") or plan.get("mode") != "layered_composite":
        errors.append({"code": "FULL_FRAME_REGEN_FORBIDDEN"})
    if plan.get("ratio") != policy.get("expected_shot_ratio"):
        errors.append({"code": "INVALID_RATIO"})

    approved = {r["id"]: r for r in authority.get("asset_rows", [])}
    actual_hashes = {r["filename"]: r["sha256"]
                     for r in authority.get("file_hashes", [])
                     if "filename" in r and "sha256" in r}
    layout = {r["id"]: (r["row"], r["order"]) for r in policy.get("layout", [])}
    required_props = policy.get("props", {})
    required_actions = policy.get("special_actions", {})
    actors = plan.get("actors", [])
    if not isinstance(actors, list):
        actors = []
    ids = [a.get("id") for a in actors if isinstance(a, dict)]
    if len(actors) != 8 or len(set(ids)) != 8 or set(ids) != set(layout):
        errors.append({"code": "CAST_COUNT_OR_ID", "message": "Exactly BX01-BX08 once"})
    occupied = set()
    checked_source = set()

    scene = plan.get("scene", {})
    if not isinstance(scene, dict):
        scene = {}
    bg = _match_hash(root, scene.get("background_file"), scene.get("sha256"),
                     errors, "Scene background")
    scene_dimensions = _png_info(bg, errors, "scene") if bg else None
    if scene_dimensions:
        width, height, _ = scene_dimensions
        if abs(width / height - 16 / 9) > 0.02:
            errors.append({"code": "SCENE_NOT_16_9"})
    if scene.get("world_axis") != "west_shore_camera_facing_east":
        errors.append({"code": "WORLD_AXIS_CHANGED"})
    if scene.get("sun") != "upper_right" or scene.get("wind") != "right_to_left":
        errors.append({"code": "LIGHT_OR_WIND_DRIFT"})

    for actor in actors:
        if not isinstance(actor, dict):
            errors.append({"code": "BAD_ACTOR"})
            continue
        aid = actor.get("id")
        if aid not in approved or aid not in layout:
            errors.append({"code": "UNKNOWN_CHARACTER", "id": aid})
            continue
        expected_slot = layout[aid]
        slot = (actor.get("row"), actor.get("order"))
        if slot != expected_slot or slot in occupied:
            errors.append({"code": "BLOCKING_DRIFT", "id": aid})
        occupied.add(slot)
        if actor.get("special_action") != required_actions.get(aid):
            errors.append({"code": "CHARACTER_ACTION_DRIFT", "id": aid})
        if aid == "BX05" and actor.get("orientation") != "backward_facing_donkey_tail":
            errors.append({"code": "DONKEY_REVERSE_RIDING_MISSING", "id": aid})
        props = actor.get("props", [])
        if not isinstance(props, list) or len(props) != len(set(props)) or props != required_props.get(aid):
            errors.append({"code": "PROP_OWNER_OR_COUNT", "id": aid})

        canonical = approved[aid]
        sources = actor.get("sources", {})
        if not isinstance(sources, dict):
            sources = {}
        # Design approval is separate from an exact approved hero byte binding.
        # Policy requires the lock even if a caller drops it from authority/plan.
        version = policy.get("character_lock_versions", {}).get(aid)
        if version:
            lock = authority.get("character_locks", {}).get(aid, {})
            if (lock.get("lock_version") != version
                    or actor.get("lock_version") != version
                    or lock.get("approval_status") != "USER_APPROVED_DESIGN_LOCK"):
                errors.append({"code": "CHARACTER_LOCK_DRIFT", "id": aid})
            hero = lock.get("current_hero", {})
            filename, checksum = hero.get("filename"), hero.get("sha256")
            registered = [r for r in authority.get("file_hashes", [])
                          if r.get("id") == aid and r.get("role") == "current_hero"
                          and r.get("filename") == filename and r.get("sha256") == checksum]
            legacy_names = {canonical[k] for k in ("hero", "turnaround", "prop")}
            reference_names = {r.get("filename") for r in lock.get("references", [])}
            if (hero.get("binding_status") != "BOUND_TO_USER_APPROVED_BYTES"
                    or not filename or not checksum or not registered
                    or filename in legacy_names | reference_names):
                errors.append({"code": "CURRENT_APPROVED_HERO_UNBOUND", "id": aid})
            else:
                if sources.get("current_hero") != filename:
                    errors.append({"code": "SOURCE_BINDING_DRIFT", "id": aid,
                                   "role": "current_hero"})
                _match_hash(root, filename, checksum, errors, aid + " current approved hero")
            references = lock.get("references", [])
            if {r.get("role") for r in references} != set(
                    policy.get("character_reference_roles", {}).get(aid, [])):
                errors.append({"code": "LOCK_REFERENCES_MISSING", "id": aid})
            for reference in references:
                if sources.get(reference["role"]) != reference["filename"]:
                    errors.append({"code": "SOURCE_BINDING_DRIFT", "id": aid,
                                   "role": reference["role"]})
                _match_hash(root, reference["filename"], reference.get("sha256"),
                            errors, aid + " " + reference["role"])
            expected_details = policy.get("prop_details", {}).get(aid)
            if actor.get("prop_details") != expected_details:
                errors.append({"code": "PROP_STRUCTURE_OR_HOLDING_DRIFT", "id": aid})
        for role, key in (("hero", "hero"), ("views", "turnaround"), ("prop", "prop")):
            filename = canonical[key]
            if sources.get(role) != filename:
                errors.append({"code": "SOURCE_BINDING_DRIFT", "id": aid, "role": role})
            if filename not in checked_source:
                _match_hash(root, filename, actual_hashes.get(filename), errors,
                            aid + " " + role + " approved original")
                checked_source.add(filename)

        layers = actor.get("locked_layers", {})
        if not isinstance(layers, dict) or set(layers) != {"character", "prop"}:
            errors.append({"code": "MISSING_LAYER_PAIR", "id": aid})
            continue
        for layer_kind in ("character", "prop"):
            layer = layers.get(layer_kind, {})
            if not isinstance(layer, dict):
                errors.append({"code": "MISSING_LAYER", "id": aid})
                continue
            item = _match_hash(root, layer.get("file"), layer.get("sha256"), errors,
                               aid + " " + layer_kind + " protected RGBA")
            mask = _match_hash(root, layer.get("mask"), layer.get("mask_sha256"),
                               errors, aid + " " + layer_kind + " edit mask")
            dims = _png_info(item, errors, aid + " RGBA layer") if item else None
            mask_dims = _png_info(mask, errors, aid + " mask") if mask else None
            if dims:
                if dims[2] != 6:
                    errors.append({"code": "LAYER_NOT_RGBA", "id": aid})
                if scene_dimensions and dims[:2] != scene_dimensions[:2]:
                    errors.append({"code": "LAYER_CANVAS_MISMATCH", "id": aid})
            if mask_dims:
                if mask_dims[2] not in (0, 4, 6):
                    errors.append({"code": "MASK_WRONG_PNG_MODE", "id": aid})
                if dims and mask_dims[:2] != dims[:2]:
                    errors.append({"code": "MASK_CANVAS_MISMATCH", "id": aid})

    status = "BLOCKED" if errors else "PREFLIGHT_PASS"
    if phase == "postflight" and not errors:
        output = plan.get("output", {})
        if not isinstance(output, dict):
            output = {}
        rendered = _match_hash(root, output.get("file"), output.get("sha256"),
                               errors, "Candidate output")
        if rendered:
            output_info = _png_info(rendered, errors, "candidate output")
            if output_info and scene_dimensions and output_info[:2] != scene_dimensions[:2]:
                errors.append({"code": "OUTPUT_CANVAS_MISMATCH"})
        review = plan.get("review", {})
        if not isinstance(review, dict):
            review = {}
        if not isinstance(review.get("p0_count"), int) or review["p0_count"] != 0:
            errors.append({"code": "P0_NOT_CLEARED"})
        if not isinstance(review.get("p1_count"), int) or review["p1_count"] != 0:
            errors.append({"code": "P1_NOT_CLEARED"})
        role_checks = review.get("roles", {})
        for role in policy.get("review_roles", []):
            entry = role_checks.get(role, {}) if isinstance(role_checks, dict) else {}
            if not isinstance(entry, dict) or entry.get("status") != "PASS":
                pending.append({"code": "REVIEW_ROLE_PENDING", "role": role})
            elif not _safe_path(root, entry.get("evidence_file"), errors, "MISSING_REVIEW_EVIDENCE"):
                pending.append({"code": "REVIEW_EVIDENCE_PENDING", "role": role})
        individual = review.get("actor_checks", {})
        if not isinstance(individual, dict):
            individual = {}
        used_evidence = set()
        for aid in sorted(layout):
            entry = individual.get(aid, {})
            if not isinstance(entry, dict):
                entry = {}
            actor_pass = True
            fields = (policy.get("per_actor_review_required", [])
                      + policy.get("per_actor_extra_review_required", {}).get(aid, []))
            for field in fields:
                state = entry.get(field)
                if state == "FAIL":
                    errors.append({"code": "ACTOR_REVIEW_FAILED", "id": aid, "item": field})
                    actor_pass = False
                elif state != "PASS":
                    pending.append({"code": "ACTOR_REVIEW_PENDING", "id": aid, "item": field})
                    actor_pass = False
            if actor_pass:
                evidence_name = entry.get("evidence_file")
                evidence_path = _safe_path(root, evidence_name, errors, "MISSING_ACTOR_EVIDENCE")
                if evidence_path:
                    if evidence_path in used_evidence:
                        errors.append({"code": "DUPLICATE_ACTOR_EVIDENCE", "id": aid})
                    used_evidence.add(evidence_path)

        cat_checks = review.get("category_checks", {})
        for name in policy.get("post_review_required", []):
            value = cat_checks.get(name) if isinstance(cat_checks, dict) else None
            if value == "FAIL":
                errors.append({"code": "VISUAL_CHECK_FAILED", "item": name})
            elif value != "PASS":
                pending.append({"code": "VISUAL_CHECK_PENDING", "item": name})
        status = "BLOCKED" if errors else ("REVIEW_REQUIRED" if pending else "READY_FOR_USER_REVIEW")

    report = {
        "phase": phase,
        "shot_id": plan.get("shot_id"),
        "status": status,
        "issues": errors,
        "pending_manual_review": pending,
        "auto_checked": [
            "approved_source_sha256", "exact_eight_cast", "role_prop_ownership",
            "fixed_blocking", "scene_orientation", "RGBA_layer_presence_and_hash",
            "mask_presence_and_hash", "layer_canvas"
        ] + (["render_sha256", "review_record_completeness", "per_actor_evidence_completeness"] if phase == "postflight" else []),
        "visual_identity_verified_automatically": False,
        "may_generate": status == "PREFLIGHT_PASS",
        "may_submit_to_user": status == "READY_FOR_USER_REVIEW",
        "may_merge_final_or_start_i2v": False,
        "note": "No automated face comparison, action physics or visual watermark validation. Explicit user approval and I2V review remain separate.",
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="BX01-BX08 fail-closed group gate")
    parser.add_argument("--phase", choices=("preflight", "postflight"), required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--authority", type=Path,
                        default=Path("film_audit/assets/baxian_source_authority_v2_20261107.json"))
    parser.add_argument("--policy", type=Path,
                        default=Path("film_audit/assets/baxian_group_enforcement_policy_v3.json"))
    parser.add_argument("--report", type=Path, default=Path("baxian-group-gate-report.json"))
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        authority = json.loads(args.authority.read_text(encoding="utf-8"))
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        result = validate(plan, authority, policy, args.asset_root, args.phase)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {"status": "BLOCKED",
                  "issues": [{"code": "UNREADABLE_INPUT", "message": str(exc)}]}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in ("PREFLIGHT_PASS", "READY_FOR_USER_REVIEW") else 1


if __name__ == "__main__":
    raise SystemExit(main())
