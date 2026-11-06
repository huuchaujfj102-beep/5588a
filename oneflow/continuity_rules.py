"""Bounded stage-specific contracts; not a visual detector or approval."""
import re

RULE_VERSION = "2.0"
STATIC_CONTRACT = (
    "Preserve requested identity, style, text, framing and prop counts. Keep rigid "
    "parts collinear; connections, grip, support, perspective, textures, shadows "
    "and reflections coherent. For each ordinary human, each shoe has one upper "
    "and one sole; no extra feet under hems; preserve intentional limb differences. "
    "User-specified magic, levitation and transformations remain allowed."
)
MOTION_CONTRACT = (
    "Lock reference identity and connections; keep contact points and action state "
    "continuous across occlusion and cuts. Follow requested timing and camera, "
    "including static; default to static if unspecified. Allow view-dependent reflections, "
    "focus and intended effects; maintain coherent parallax."
)
STATIC_NEGATIVE = (
    "unrequested anatomy or prop changes, disconnected parts, interpenetration, "
    "malformed grips, misaligned rigid parts, duplicated soles, extra shoes under hems, "
    "warped textures, contradictory perspective, unrequested or mirrored lettering, "
    "incoherent shadows"
)
MOTION_NEGATIVE = (
    "unexplained prop morphing, unexplained teleportation or disappearance, "
    "contact drift, foot sliding, texture flicker, camera tearing, unmotivated focus or color jumps"
)
SPECIALISTS = (
    (("背剑", "背劍", "背负大剑", "背負大劍", "背负长剑", "背負長劍",
      "背负纯阳剑", "背負純陽劍", "back sword", "back-mounted sword", "sword on back"),
     "Back sword: grip/guard/mouth/sheath on one straight axis; secure harness; "
     "occluded sheath stays hidden, not offset."),
    (("拂尘", "拂塵", "fly-whisk", "fly whisk"),
     "Fly-whisk: one handle, hair attached at ONE end only; grip bare shaft, bare butt."),
    (("花篮", "花籃", "flower basket"),
     "Basket: closed base, one arch fixed at both rim ends, distinct supporting fingers; "
     "flower spiral stems connect inside basket."),
    (("倒骑", "倒騎", "riding backwards"),
     "Backward riding: chest/knees face opposite specified mount head; plausible "
     "seat and legs; preserve mount species and count."),
)


def specialist_constraints(text):
    """Conservative local clause matching; ambiguous prose still needs review."""
    clauses = re.split(r"[。；;!！?？\n]+", text.casefold())
    selected = []
    for keys, rule in SPECIALISTS:
        for clause in clauses:
            for key in keys:
                for match in re.finditer(re.escape(key), clause):
                    before = clause[max(0, match.start()-35):match.start()]
                    after = clause[match.end():match.end()+12]
                    if re.search(r"(?:不要|禁止|无|無|不带|不帶|不持|不拿|移除|去掉|没有|沒有)\s*$", before):
                        continue
                    if re.search(r"(?:\bno|\bwithout|\bremove|\bavoid|\bnot holding)\s+(?:(?:a|the|any)\s+)?$", before):
                        continue
                    if re.match(r"\s*(?:不入镜|不入鏡|未出现|未出現|不存在|不在本镜|不在本鏡|not visible)", after):
                        continue
                    selected.append(rule)
                    break
                if rule in selected:
                    break
            if rule in selected:
                break
    return " ".join(selected)


def prompt_constraints(text, motion=False):
    return " ".join(x for x in (STATIC_CONTRACT, MOTION_CONTRACT if motion else "",
                                 specialist_constraints(text)) if x)


def negative_constraints(motion=False):
    return STATIC_NEGATIVE + (", " + MOTION_NEGATIVE if motion else "")


_BLOCK = re.compile(r"\n\[OneFlow rules v2:(?:image|video):(?:inline|separate)\]\n.*?\n\[/OneFlow rules\]\s*\Z", re.S)


def compile_prompt(text, *, stage="image", max_chars=None, separate_negative=False):
    """Shrink only our rules or fail; never truncate the user's source."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Prompt must be nonempty text")
    if stage not in ("image", "video"):
        raise ValueError("Unknown generation stage")
    if max_chars is not None and (type(max_chars) is not int or max_chars < 4):
        raise ValueError("Invalid prompt character budget")
    source = _BLOCK.sub("", text)
    motion = stage == "video"
    mode = "separate" if separate_negative else "inline"
    negative = negative_constraints(motion)
    start = "\n[OneFlow rules v2:" + stage + ":" + mode + "]\n"
    end = "\n[/OneFlow rules]"
    compact = (
        "Honor requested style/framing/text/magic. Keep counts, rigid axes, connections, "
        "grip, feet/shoes, contact, perspective and light coherent. " +
        ("Lock reference identity; preserve action state across occlusion; "
         "follow requested camera; no unexplained jumps. " if motion else "") +
        specialist_constraints(source)
    )
    for contract in (prompt_constraints(source, motion), compact):
        prompt = source + start + contract
        if not separate_negative:
            prompt += " Avoid: " + negative
        prompt += end
        if max_chars is None or len(prompt) <= max_chars:
            return {"prompt": prompt, "negative_prompt": negative,
                    "rule_version": RULE_VERSION, "negative_mode": mode}
    raise ValueError("Prompt with required rules exceeds " + str(max_chars) +
                     " characters; shorten the brief or split shot (source not truncated)")


REVIEW_CHECKLIST = (
    "Images are head, tail, head lower-frame detail, tail lower-frame detail. "
    "Detail crops come from the SAME two moments; no extra time coverage. "
    "Check visible identity/counts, prop axes/connections, "
    "grip, limb chains, space, textures, light and reflections. Inspect feet enlarged: "
    "count shoe uppers, soles, toe/heel fragments under hems, match each to one foot "
    "and check contact. Do not invent hidden ankles or mistake cloth for confirmed "
    "feet. Apply relevant prop checks only: collinear sword, single-ended whisk, "
    "attached basket handle. Respect requested style/text/magic and normal changes. "
    "Cite head/tail and region in findings; ambiguous occlusion goes in uncertainties. "
    "Two stills cannot verify flicker, intervening motion, full camera continuity or every frame."
)

