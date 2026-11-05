"""Cinematic prompt policy V2.1. Text controls, not a rendered-image certification.

Full positive and negative masters:
docs/cinematic-positive-global-prompt.md
docs/cinematic-negative-suppression-prompt.md
"""
GLOBAL_PREFIX = (
    "CINEMATIC SERIES GLOBAL RULES: preserve approved character face, outfit, "
    "vehicle topology, exact set layout, prop inventory and narrative world state "
    "across adjacent shots. Anatomically plausible connected joints and fingers; "
    "stable rigid geometry, realistic support, contact and clean occlusion. "
    "One consistent camera projection, appropriate perspective, focus and depth "
    "of field; motivated primary and fill light, coherent shadows/reflections, "
    "physically plausible PBR and volume scattering. Maintain approved camera "
    "side, scene time, continuity and action order; treat fantasy exceptions "
    "as explicitly approved story physics. Exact lettering and watermarks belong "
    "to approved assets or compositing. Cinematic detailed texture and natural "
    "color, using the actual model output resolution rather than claiming 8K."
)
NEGATIVE_LAYERS = {
    "A": ("anatomical defect, extra limbs, fused fingers, inverted palm, "
          "duplicated face, penetrating geometry, floating props, "
          "broken mechanical parts, identity drift"),
    "B": ("broken occlusion, incompatible camera perspective, incorrect scale, "
          "contradictory motivated light and shadows, impossible reflection, "
          "teleporting assets, inconsistent action order"),
    "C": ("garbled text, inaccurate logo, fake PBR, stretched texture, "
          "billboard smoke, inconsistent depth of field, aberrations, "
          "moire, color banding, compression artifacts"),
    "D": ("unwanted toy cartoon look, plastic skin, oversaturation, "
          "clipped highlights, crushed shadows, noisy grain, blurry subject"),
}
NEGATIVE_WEIGHTS = {"A": 1.4, "B": 1.3, "C": 1.15, "D": 1.0}
NEGATIVE_HINT = "; ".join(NEGATIVE_LAYERS.values())


def build_negative_prompt(*, weighted=False, exclude_layers=()):
    """Use weighted=True ONLY for validated provider weight syntax."""
    excluded = set(exclude_layers)
    if excluded - set(NEGATIVE_LAYERS):
        raise ValueError("Unknown negative prompt layer")
    parts = []
    for layer, value in NEGATIVE_LAYERS.items():
        if layer in excluded:
            continue
        parts.append(f"({value}:{NEGATIVE_WEIGHTS[layer]})" if weighted else value)
    return "; ".join(parts)


def apply_global_rules(prompt):
    """Prepend once; compatibility with prior OneFlow integration."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Image prompt must be non-empty")
    if prompt.startswith(GLOBAL_PREFIX):
        return prompt
    return GLOBAL_PREFIX + "\n" + prompt
