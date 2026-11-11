"""Evidence-only Baxian V3.1-V3.5 scene contract gate.

Does NOT inspect pixels or footage and cannot approve visual quality.
Only validates signed-off metadata prerequisites for sending a protected shot.
"""
import re

REQUIRED_CONTRACT = (
    "period_system", "aspect_ratio", "camera_axis", "physical_key_light",
    "ground_surfaces", "fog_layers", "wind_vector", "faction_palette",
)
REQUIRED_POSITION = ("character_id", "master_sha256", "artifact_group",
                     "facing", "depth_layer", "occlusion")
HARD_CHECKS = {
    "G4S": ("source_identity", "costume_material", "light_source", "force_grounding"),
    "G4M": ("grip_and_artifact", "shadows", "occlusion", "directional_force"),
    "G4B": ("eight_asset_groups", "lotus_basket_ownership", "master_appearance",
            "donkey_lotus_contact"),
    "G4D": ("story_phase", "camera_axis", "target_and_intent"),
}
ALLOWED_PHASES = ("ASSEMBLED_8", "CAPTURE_EVENT", "RESCUE_7", "REUNITED_8",
                  "OTHER_APPROVED_V3")
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class BaxianSceneGateError(ValueError):
    pass


def _need(obj, key, label):
    value = obj.get(key) if isinstance(obj, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise BaxianSceneGateError("BLOCKED: " + label + "." + key + " missing")
    return value


def check_baxian_scene(doc):
    """Validate required metadata with fail-closed story and identity semantics."""
    contract = doc.get("battlefield_contract")
    if not isinstance(contract, dict):
        raise BaxianSceneGateError("BLOCKED: battlefield_contract missing")
    for field in REQUIRED_CONTRACT:
        _need(contract, field, "battlefield_contract")
    if contract["aspect_ratio"] != "16:9":
        if not (doc.get("aspect_change_order") == "APPROVED" and
                doc.get("aspect_change_reviewer")):
            raise BaxianSceneGateError("BLOCKED: non-16:9 requires approved change order")
    positions = doc.get("character_positions")
    if not isinstance(positions, list) or not positions:
        raise BaxianSceneGateError("BLOCKED: character_positions missing")
    asset_map = {x.get("asset_id"): x.get("sha256") for x in doc["assets"]}
    present = set()
    for pos in positions:
        for field in REQUIRED_POSITION:
            _need(pos, field, "character_positions")
        ident = pos["character_id"]
        if ident in present or not re.fullmatch(r"BX0[1-8]", ident):
            raise BaxianSceneGateError("BLOCKED: duplicated/invalid Baxian character")
        present.add(ident)
        if pos["master_sha256"].lower() != str(asset_map.get(ident, "")).lower():
            raise BaxianSceneGateError("BLOCKED: position master hash differs from locked asset")
        if not HEX64.fullmatch(pos["master_sha256"]):
            raise BaxianSceneGateError("BLOCKED: invalid master sha")
    phase = doc.get("story_phase")
    if phase not in ALLOWED_PHASES:
        raise BaxianSceneGateError("BLOCKED: story_phase missing or unsupported")
    if phase == "RESCUE_7" and "BX04" in present:
        raise BaxianSceneGateError("BLOCKED: captured BX04 cannot be in rescue fighting formation")
    if phase == "RESCUE_7" and doc.get("script_change_order") != "APPROVED":
        raise BaxianSceneGateError("BLOCKED: capture arc not approved for V3")
    if phase == "ASSEMBLED_8" and len(present) != 8:
        raise BaxianSceneGateError("BLOCKED: eight-person assembly has missing characters")
    evidence = doc.get("supplemental_gates")
    if not isinstance(evidence, dict):
        raise BaxianSceneGateError("REVIEW_REQUIRED: G4S/G4M/G4B/G4D/G4C evidence missing")
    for group, checks in HARD_CHECKS.items():
        entries = evidence.get(group)
        if not isinstance(entries, dict):
            raise BaxianSceneGateError("REVIEW_REQUIRED: missing " + group)
        for check in checks:
            if entries.get(check) != "PASS":
                raise BaxianSceneGateError("REVIEW_REQUIRED: " + group + "." + check)
    cinema = evidence.get("G4C")
    if not isinstance(cinema, dict):
        raise BaxianSceneGateError("REVIEW_REQUIRED: G4C cinema assessment missing")
    if cinema.get("reviewed") != "PASS" or cinema.get("hard_defects") != 0:
        raise BaxianSceneGateError("REVIEW_REQUIRED: G4C hard defects or unreviewed")
    if not isinstance(cinema.get("art_notes"), str):
        raise BaxianSceneGateError("REVIEW_REQUIRED: G4C art observations required")
    return {"supplemental_evidence": "METADATA_VERIFIED_NOT_VISUAL_QA",
            "checked_groups": tuple(HARD_CHECKS) + ("G4C",)}
