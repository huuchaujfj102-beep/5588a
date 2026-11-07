"""Non-generative compositor for eight locked RGBA actor/prop layers.

Inputs must first pass baxian_group_gate PRE-FLIGHT.
Does not regenerate faces, bodies, costume, props or the source scene.
Pillow is optional for the repository overall and required for this command.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from film_audit.baxian_group_gate import validate


def _load_image_tools():
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise RuntimeError("Pillow is required for this image compositor; install Pillow") from exc
    return Image, ImageChops


def composite_locked_layers(plan: dict, authority: dict, policy: dict,
                            asset_root: Path, output_name: str) -> dict:
    """Renders one independent PNG without whole-frame generative repaint."""
    root = asset_root.resolve()
    pre = validate(plan, authority, policy, root, "preflight")
    if pre["status"] != "PREFLIGHT_PASS":
        return {
            "status": "BLOCKED",
            "reason": "Pre-generation asset gate failed; see gate_issues",
            "gate_issues": pre["issues"],
        }

    Image, ImageChops = _load_image_tools()
    declared_out = plan.get("output", {}).get("file")
    if output_name != declared_out or not isinstance(output_name, str):
        return {"status": "BLOCKED", "reason": "Render output path does not match shot manifest"}
    out = (root / output_name).resolve()
    if not out.is_relative_to(root) or not out.relative_to(root).parts or out.relative_to(root).parts[0] != "outputs":
        return {"status": "BLOCKED", "reason": "Output is restricted to asset_root/outputs"}
    if out.exists():
        return {"status": "BLOCKED", "reason": "Refuse overwrite: only new candidate filename allowed"}

    with Image.open(root / plan["scene"]["background_file"]) as background:
        canvas = background.convert("RGBA")

    def apply_layer(layer: dict):
        nonlocal canvas
        with Image.open(root / layer["file"]) as raw:
            rgba = raw.convert("RGBA")
        with Image.open(root / layer["mask"]) as masked:
            mask = masked.getchannel("A") if masked.mode in ("RGBA", "LA") else masked.convert("L")
        if rgba.size != canvas.size or mask.size != canvas.size:
            raise ValueError("Compositor canvas dimensions drifted")
        matte_range = mask.getextrema()
        layer_range = rgba.getchannel("A").getextrema()
        if matte_range in ((0, 0), (255, 255)) or layer_range in ((0, 0), (255, 255)):
            raise ValueError("Unsegmented or empty layer/mask; mask must be meaningful")
        rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), mask))
        canvas = Image.alpha_composite(canvas, rgba)

    # Approved actors move through a fixed z-order. Prop exceptions are explicit.
    prop_behind = {"BX02", "BX05", "BX07"}
    back_to_front = sorted(
        plan["actors"],
        key=lambda actor: (0 if actor["row"] == "back" else 1, actor["order"])
    )
    try:
        for actor in back_to_front:
            layers = actor["locked_layers"]
            if actor["id"] in prop_behind:
                apply_layer(layers["prop"])
                apply_layer(layers["character"])
            else:
                apply_layer(layers["character"])
                apply_layer(layers["prop"])
    except (OSError, ValueError) as exc:
        return {"status": "BLOCKED", "reason": str(exc)}

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, format="PNG")
    checksum = hashlib.sha256(out.read_bytes()).hexdigest()
    return {
        "status": "CANDIDATE_RENDERED_NOT_APPROVED",
        "shot_id": plan.get("shot_id"),
        "output_file": output_name,
        "sha256": checksum,
        "size": list(canvas.size),
        "layers_composited": len(back_to_front) * 2,
        "next_gate": "Run postflight after adding output.sha256 and seven-role evidence",
        "may_start_i2v": False,
        "note": "No AI redraw performed. Approval still requires actual face/prop visual comparison by reviewer and explicit user confirmation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="BX01-BX08 approved-layer only compositor")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--authority", type=Path, default=Path("film_audit/assets/baxian_source_authority_v2_20261107.json"))
    parser.add_argument("--policy", type=Path, default=Path("film_audit/assets/baxian_group_enforcement_policy_v3.json"))
    parser.add_argument("--report", type=Path, default=Path("baxian-composite-report.json"))
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        authority = json.loads(args.authority.read_text(encoding="utf-8"))
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        result = composite_locked_layers(
            plan, authority, policy, args.asset_root,
            plan.get("output", {}).get("file", "")
        )
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "CANDIDATE_RENDERED_NOT_APPROVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
