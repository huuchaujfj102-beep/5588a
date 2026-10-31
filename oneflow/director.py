"""Director prompt contract: seven ordered modules and user-locked asset truth."""
import re

NEGATIVE = (
    "unapproved new actors or props; changed identities; extra wheels or engines; "
    "backwards action order; inconsistent camera side; deformed anatomy/vehicle; "
    "teleportation; duplicate characters; unreadable signs; unauthorized logos; watermarks"
)


def phase_list(brief):
    phases = [s.strip() for s in re.split(r"[，,。；;！!？?\n]+", brief) if s.strip()]
    return phases or [brief.strip()]


def film_prompt(brief, shot_focus, prior_focus, shot_no, shot_total):
    """A conservative prompt wrapper; no claim that it ensures perfect continuity."""
    parts = [
        "1. Original image/asset lock: Original approved references, character identities, "
        "face geometry, clothing, props, vehicle geometry, scene orientation, and aspect "
        "ratio MUST remain unchanged. User brief is the source of truth: " + brief,
        "2. Local micro-motion: Render only the requested physical action for this shot, "
        "with plausible acceleration, forces and object contacts. Shot focus: " + shot_focus,
        "3. Environment dynamics: Only environmental elements explicitly established "
        "by the brief may move; preserve geography and object positions.",
        "4. Single controlled camera move: One coherent deliberate camera movement, "
        "no sudden contradictory perspective swap.",
        "5. Lighting: Keep direction, time of day, practical lights and color consistent "
        "with approved preceding frames.",
        "6. Video quality: Photorealistic cinematic motion, clear frame, consistent "
        "subject design, smooth temporal transition. Shot " + str(shot_no) + "/" +
        str(shot_total) + ". Prior narrative phase: " + (prior_focus or "none") + ".",
        "7. Negative constraints: " + NEGATIVE
    ]
    return "\n".join(parts)
