"""Shared prompt additions, not a visual detector or an approval mechanism."""

STATIC_CONTRACT = (
    "Keep prop counts, scale, parts and connections coherent; straight rigid parts "
    "stay collinear across occlusion. Show credible grip, support and contact; "
    "separate fingers from props. Preserve scene perspective, roads, stairs and "
    "surface-attached textures. Light, shadows and reflections must agree with "
    "geometry. Frame required props and feet without accidental cropping. "
    "User-specified magic, levitation and transformations remain allowed."
)
MOTION_CONTRACT = (
    "Across frames and cuts preserve identity, prop design and connections, "
    "contact points and action state, including after occlusion. Use one slow "
    "continuous camera move; keep parallax and spatial order coherent. Allow "
    "view-dependent reflections, focus changes and intended motion; reject only "
    "unexplained discontinuities, foot sliding, resets and texture flicker."
)
STATIC_NEGATIVE = (
    "interpenetration, disconnected parts, unsupported non-magical props, "
    "wrong prop counts, malformed grips, misaligned rigid parts, warped textures, "
    "contradictory perspective, mirrored lettering, incoherent shadows"
)
MOTION_NEGATIVE = (
    "unexplained prop morphing, teleportation, contact drift, foot sliding, "
    "disappearing props, texture flicker, camera tearing, unmotivated focus or color jumps"
)

SPECIALISTS = (
    (("背剑", "背負", "背负", "back sword", "back-mounted sword"),
     "Back sword: one sheathed sword, grip/guard/mouth/sheath on one straight axis; "
     "secure harness. Hidden segments stay hidden rather than appearing misaligned."),
    (("拂尘", "拂塵", "fly-whisk", "fly whisk"),
     "Fly-whisk: one continuous handle, hair attached at ONE end only; "
     "hand grips bare shaft, opposite butt is bare. Keep hair separate from beard."),
    (("花篮", "花籃", "flower basket"),
     "Basket: one arched handle attached at both rim ends, coherent closed base; "
     "readable gripping and supporting fingers. Any flower spiral stems connect inside basket."),
    (("倒骑", "倒騎", "riding backwards"),
     "Backward riding: rider chest and knees face opposite the donkey head; "
     "plausible seat and legs, one rider and one four-legged donkey."),
)


def specialist_constraints(text):
    lowered = text.casefold()
    return " ".join(rule for keys, rule in SPECIALISTS
                    if any(key in lowered for key in keys))


def prompt_constraints(text, motion=False):
    parts = [STATIC_CONTRACT]
    if motion:
        parts.append(MOTION_CONTRACT)
    extra = specialist_constraints(text)
    if extra:
        parts.append(extra)
    return " ".join(parts)


def negative_constraints(motion=False):
    return STATIC_NEGATIVE + (", " + MOTION_NEGATIVE if motion else "")


REVIEW_CHECKLIST = (
    "Check visible prop parts/counts, sword-axis alignment, single-ended whisk hair, "
    "basket attachments, grip/contact and limb chains, scene perspective, stairs, "
    "surface textures, shadows and reflections. Respect brief-defined magic and "
    "normal view-dependent changes. Identify frame head/tail and image region in "
    "each supported finding; uncertain occluded details go in uncertainties. "
    "Two stills cannot verify flicker, full motion, camera continuity or every frame."
)
