import hashlib
import json
from pathlib import Path

GATES = (
    "story_prompt", "content_compliance_copyright", "cast_continuity",
    "visual_physics", "lipsync_audio_subtitles", "ocr_watermark_media",
    "final_review",
)


def issue(code, message, path=None):
    item = {"severity": "blocker", "code": code, "message": message}
    if path:
        item["path"] = path
    return item


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_file(root, record, label):
    problems = []
    rel = (record or {}).get("file")
    expected = (record or {}).get("sha256", "").lower()
    if not rel or not expected:
        return [issue("MISSING_FILE_PROOF", f"{label}缺文件路径或SHA-256")]
    target = root / rel
    if not target.is_file():
        return [issue("MISSING_FILE", f"{label}文件不存在", rel)]
    if sha256(target) != expected:
        problems.append(issue("HASH_MISMATCH", f"{label}哈希不符", rel))
    return problems


def verify_evidence(manifest_path):
    root = manifest_path.parent
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [issue("BAD_EVIDENCE_MANIFEST", str(exc))]

    problems = []
    rules = data.get("rules", [])
    numbers = [r.get("number") for r in rules]
    if numbers != list(range(1, 68)):
        problems.append(issue("RULES_NOT_67", "必须提供按1至67连续编号的规则原文"))
    for r in rules:
        if not all(str(r.get(k, "")).strip() for k in ("text", "version", "approved_by", "approved_at")):
            problems.append(issue("RULE_APPROVAL_INCOMPLETE", f"规则{r.get('number')}缺原文或批准信息"))

    assets = data.get("approved_assets", [])
    if not assets:
        problems.append(issue("NO_APPROVED_ASSETS", "缺批准资产登记"))
    seen = set()
    for a in assets:
        aid = str(a.get("asset_id", "")).strip()
        required = (aid, a.get("category"), a.get("approved_by"), a.get("approved_at"))
        if not all(str(v or "").strip() for v in required):
            problems.append(issue("ASSET_APPROVAL_INCOMPLETE", f"资产{aid or '[无ID]'}批准信息不完整"))
        if aid in seen:
            problems.append(issue("DUPLICATE_ASSET_ID", f"资产ID重复：{aid}"))
        seen.add(aid)
        problems += verify_file(root, a, f"资产{aid}")

    axis = data.get("axis_diagram")
    problems += verify_file(root, axis, "轴线图")
    if axis and not axis.get("camera_map_complete"):
        problems.append(issue("CAMERA_MAP_INCOMPLETE", "轴线图未逐镜标注机位/朝向"))

    shots = data.get("generation_parameters", [])
    required_shots = {(ep, n) for ep in range(1, 5) for n in range(1, 33)}
    actual_shots = {(s.get("episode"), s.get("shot")) for s in shots}
    if actual_shots != required_shots:
        problems.append(issue("GENERATION_PARAMETERS_INCOMPLETE", "必须提交四回各32镜生成参数"))
    fields = ("platform", "model", "model_version", "seed", "prompt", "duration", "fps", "output_sha256")
    for s in shots:
        if not all(str(s.get(k, "")).strip() for k in fields):
            problems.append(issue("SHOT_PARAMETERS_INCOMPLETE", f"第{s.get('episode')}回第{s.get('shot')}镜参数不完整"))

    films = data.get("final_films", [])
    if {f.get("episode") for f in films} != {1, 2, 3, 4}:
        problems.append(issue("FINAL_FILMS_INCOMPLETE", "必须提交四回正式成片"))
    for f in films:
        problems += verify_file(root, f, f"第{f.get('episode')}回成片")
        if not all(f.get(k) for k in ("duration", "resolution", "fps", "timecode_map")):
            problems.append(issue("FILM_METADATA_INCOMPLETE", f"第{f.get('episode')}回成片元数据不完整"))

    reviews = data.get("human_reviews", [])
    required_roles = {"story", "continuity", "cooking"}
    film_hashes = {f.get("sha256", "").lower() for f in films}
    for ep in range(1, 5):
        current = [r for r in reviews if r.get("episode") == ep]
        if {r.get("role") for r in current} != required_roles:
            problems.append(issue("HUMAN_REVIEWS_INCOMPLETE", f"第{ep}回缺三方人工看片"))
        for r in current:
            if r.get("decision") != "PASS" or not all(r.get(k) for k in ("reviewer", "reviewed_at", "film_sha256")):
                problems.append(issue("HUMAN_REVIEW_NOT_PASS", f"第{ep}回{r.get('role')}未有效签核"))
            if str(r.get("film_sha256", "")).lower() not in film_hashes:
                problems.append(issue("REVIEW_HASH_MISMATCH", f"第{ep}回看片版本与成片哈希不匹配"))

    gates = data.get("gates", {})
    for gate in GATES:
        record = gates.get(gate, {})
        if record.get("decision") != "PASS" or not all(record.get(k) for k in ("approved_by", "approved_at", "evidence")):
            problems.append(issue("GATE_NOT_APPROVED", f"关卡{gate}未批准"))
    return problems


def build_result(manifest_path):
    problems = verify_evidence(Path(manifest_path))
    return {
        "status": "PASS" if not problems else "FAIL",
        "scope": "V5.2 production evidence",
        "issues": problems,
        "rule": "只有真实文件、哈希匹配、67条规则、四回参数/成片及三方人工签核全部齐备时才可PASS",
    }

