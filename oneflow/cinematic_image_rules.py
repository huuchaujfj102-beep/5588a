"""Cinematic still-image prompt constraints. Advisory text; not an image validator.

Keep this prefix compact for model attention. Full human QA checklist:
docs/cinematic-image-rules-v2.md
"""
GLOBAL_PREFIX = (
    "CINEMATIC STILL FRAME RULES: preserve approved character identity, wardrobe, "
    "vehicle/prop topology and scene layout; one coherent camera viewpoint and "
    "physically plausible scale, occlusion, contact and anatomy; visible hands have "
    "correct connected digits; fixed parts and accessory attachment points; "
    "consistent motivated key/fill lighting, shadow direction, reflections, PBR "
    "material response and believable atmospheric perspective. Camera optics, "
    "focus and depth of field must agree with the shot; no accidental text. "
    "Maintain continuity with the approved shot bible; intentional fantasy "
    "exceptions must follow the story's stated physics."
)
NEGATIVE_HINT = (
    "extra or fused fingers, duplicate faces or limbs, warped eyes, floating props, "
    "intersecting geometry, melting machinery, random vehicle wheels, inconsistent "
    "vanishing geometry, contradictory shadows, inaccurate reflections, plastic "
    "skin or metal, noisy fake texture, garbled text, unintended logos or watermark, "
    "identity drift, costume drift, displaced doors or windows, teleporting assets"
)

def apply_global_rules(prompt):
    """Prefix plain prompt once; never claim the model has passed QA."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Image prompt must be non-empty")
    if prompt.startswith(GLOBAL_PREFIX):
        return prompt
    return GLOBAL_PREFIX + "\n" + prompt
