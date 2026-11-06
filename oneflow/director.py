"""Director prompt contract: seven ordered modules and user-locked asset truth."""
import re
from .continuity_rules import compile_prompt

NEGATIVE = "unapproved new actors or props; changed identities; unexplained action resets"


def phase_list(brief):
    phases = [s.strip() for s in re.split(r"[，,。；;！!？?\n]+", brief) if s.strip()]
    return phases or [brief.strip()]


def film_prompt(brief, shot_focus, prior_focus, shot_no, shot_total):
    """A conservative prompt wrapper; no claim that it ensures perfect continuity."""
    parts = [
        "1. Original image/asset lock: Approved identity, clothing, props and scene. "
        "User brief is source of truth: " + brief,
        "2. Local micro-motion: Requested action only, coherent support/contact. Shot focus: " + shot_focus,
        "3. Environment dynamics: Preserve layout; allow requested environmental motion.",
        "4. Single controlled camera move: Follow requested camera, including static; "
        "default to static if unspecified; no unexplained axis reversal.",
        "5. Lighting: Coherent sources; allow motivated time/light/view changes.",
        "6. Video quality: Requested style, readable subjects, smooth transition. Shot " +
        str(shot_no) + "/" + str(shot_total) + ". Prior narrative phase: " + (prior_focus or "none") + ".",
        "7. Negative constraints: " + NEGATIVE
    ]
    return compile_prompt("\n".join(parts), stage="video")["prompt"]
