"""Image-to-video temporal prompt policy V3.0 (advisory text, not QA)."""

TEMPORAL_PREFIX = (
    "CINEMATIC I2V REFERENCE LOCK: The approved source still is the first-frame "
    "source of truth. Preserve face identity, wardrobe, scene layout, rigid "
    "geometry, prop attachment, camera side and narrative action state. "
    "Animate only scripted subject and environment movement with plausible "
    "articulation, contact, inertia and acceleration; no autonomous morphing "
    "of static architecture or machinery. Use one motivated camera move, "
    "coherent projection and parallax. Maintain time-continuous motivated "
    "lighting, shadows, reflection behavior, PBR response, exposure, focus "
    "and optical motion blur. Cloth, hair and particles respond to established "
    "forces continuously, with no random frame refresh. Preserve story-approved "
    "fantasy exceptions. No frame flicker, topology drift or scene reconstruction."
)
TEMPORAL_NEGATIVE_LAYERS = {
    "A": "temporal flicker, identity drift, face swap, rigid structure morphing, "
         "finger count changes, prop teleportation, world layout rebuilding, severe geometry clipping",
    "B": "shadow jumping, exposure pumping, material shimmer, implausible parallax, "
         "optical flow explosion, motion blur ghosting, unmotivated jitter, hair or cloth twitch, volumetric flashing",
    "C": "compression blocks, noisy grain chatter, color banding, excess lens flare, unwanted style change"
}
TEMPORAL_NEGATIVE_WEIGHTS = {"A": 1.4, "B": 1.2, "C": 1.0}


def apply_temporal_rules(prompt):
    """Prefix exactly once; do not claim the backend enforces constraints."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Video prompt must be non-empty")
    if prompt.startswith(TEMPORAL_PREFIX):
        return prompt
    return TEMPORAL_PREFIX + "\n" + prompt


def build_temporal_negative(*, weighted=False, exclude_layers=()):
    """Use weighted version only after provider syntax verification."""
    excluded = set(exclude_layers)
    if excluded - set(TEMPORAL_NEGATIVE_LAYERS):
        raise ValueError("Unknown temporal negative layer")
    return "; ".join(
        (f"({value}:{TEMPORAL_NEGATIVE_WEIGHTS[layer]})" if weighted else value)
        for layer, value in TEMPORAL_NEGATIVE_LAYERS.items()
        if layer not in excluded
    )


def source_frame_gate(status):
    """External workflow must supply true human attestation; never synthesize PASS."""
    if status != "PASS_HUMAN":
        raise ValueError("Approved source image required for I2V; REVIEW_REQUIRED")
    return True
