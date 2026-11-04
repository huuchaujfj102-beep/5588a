"""Offline long-form episode and shot database for OneFlow.

Independent of oneflow.core.create (which deliberately caps short-film jobs).
No provider calls, GPU inference, model downloads or publication occur here.
"""
import argparse
import hashlib
import ipaddress
import json
import math
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

MAX_EPISODE_SECONDS = 1200
MAX_SHOTS = 200
DURATIONS_7MIN = (35, 50, 55, 60, 70, 75, 75)

DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS episodes (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, brief TEXT NOT NULL,
 seconds INTEGER NOT NULL, ratio TEXT NOT NULL,
 schema_version TEXT NOT NULL, status TEXT NOT NULL,
 plan_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scenes (
 id TEXT PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(id),
 chapter_no INTEGER NOT NULL, scene_no INTEGER NOT NULL,
 beat TEXT NOT NULL, seconds INTEGER NOT NULL,
 UNIQUE(episode_id, scene_no));
CREATE TABLE IF NOT EXISTS shots (
 id TEXT PRIMARY KEY, scene_id TEXT NOT NULL REFERENCES scenes(id),
 shot_no INTEGER NOT NULL, seconds INTEGER NOT NULL,
 visual_prompt TEXT NOT NULL, status TEXT NOT NULL,
 UNIQUE(scene_id, shot_no));
CREATE TABLE IF NOT EXISTS assets (
 shot_id TEXT PRIMARY KEY REFERENCES shots(id),
 kind TEXT NOT NULL CHECK(kind IN ('image','video')),
 source_url TEXT NOT NULL,
 rights_ref TEXT NOT NULL,
 sha256 TEXT,
 status TEXT NOT NULL CHECK(status = 'RIGHTS_REVIEWED'));
CREATE TABLE IF NOT EXISTS render_jobs (
 id TEXT PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(id),
 provider TEXT NOT NULL, status TEXT NOT NULL,
 request_digest TEXT NOT NULL, remote_id TEXT,
 receipt_json TEXT, cost_actual REAL, currency TEXT);
CREATE TABLE IF NOT EXISTS model_jobs (
 id TEXT PRIMARY KEY, episode_id TEXT NOT NULL REFERENCES episodes(id),
 shot_id TEXT REFERENCES shots(id), backend TEXT NOT NULL,
 status TEXT NOT NULL, model_version TEXT,
 rights_checked INTEGER NOT NULL DEFAULT 0,
 cost_actual REAL, currency TEXT);
"""


class LongformError(ValueError):
    pass


def _id(title, brief, seconds):
    return "EP-" + hashlib.sha256(
        (title.strip() + "\n" + brief.strip() + "\n" + str(seconds)).encode("utf-8")
    ).hexdigest()[:12]


def _durations(seconds):
    if seconds == 420:
        return list(DURATIONS_7MIN)
    if seconds == 1200:
        return [75] * 16
    count = min(20, max(1, math.ceil(seconds / 60)))
    base, extra = divmod(seconds, count)
    return [base + (i < extra) for i in range(count)]


def make_plan(title, brief, seconds=420, ratio="16:9", scene_beats=None):
    if not isinstance(seconds, int) or not 15 <= seconds <= MAX_EPISODE_SECONDS:
        raise LongformError("Episode must be 15-1200 integer seconds")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
        raise LongformError("Invalid title")
    if not isinstance(brief, str) or not 4 <= len(brief.strip()) <= 2000:
        raise LongformError("Brief must be 4-2000 characters")
    if ratio not in ("16:9", "9:16"):
        raise LongformError("Only 16:9 or 9:16 supported")
    durations = _durations(seconds)
    if scene_beats is not None and (
        not isinstance(scene_beats, list)
        or len(scene_beats) != len(durations)
        or not all(isinstance(b, str) and 1 <= len(b.strip()) <= 500 for b in scene_beats)
    ):
        raise LongformError("scene_beats must match planned scene count")
    ident = _id(title, brief, seconds)
    scenes = []
    shot_total = 0
    for index, duration in enumerate(durations, 1):
        chapter = (index - 1) // 4 + 1 if seconds == 1200 else 1
        beat = scene_beats[index - 1].strip() if scene_beats is not None else (
            "Scene outline required: develop original plot and approve before media production."
        )
        sid = f"{ident}-C{chapter:02d}-S{index:02d}"
        count = math.ceil(duration / 9)
        base, remainder = divmod(duration, count)
        shots = []
        for j in range(count):
            shot_seconds = base + (j < remainder)
            shots.append({
                "id": f"{sid}-H{j + 1:03d}", "seconds": shot_seconds,
                "status": "PLANNED",
                "visual_prompt": (
                    f"{beat} | SHOT {j + 1}/{count}. Source brief: {brief.strip()}. "
                    "Lock character references, background layout and wardrobe; "
                    "one slow camera movement; preserve realistic lighting; "
                    "no duplicated limbs, frame drift, text or watermarks."
                )
            })
        shot_total += count
        scenes.append({
            "id": sid, "chapter_no": chapter, "scene_no": index,
            "seconds": duration, "beat": beat, "shots": shots
        })
    if shot_total > MAX_SHOTS:
        raise LongformError("Shot count exceeds 200; split into separate episodes")
    return {
        "schema": "oneflow.longform.v1", "id": ident, "title": title.strip(),
        "brief": brief.strip(), "seconds": seconds, "ratio": ratio,
        "status": "PLANNED_OFFLINE_NOT_RENDERED",
        "planner": "deterministic_skeleton_not_ai_storyboard",
        "scenes": scenes, "shots_count": shot_total,
        "gates": {
            "paid_inference": "NOT_AUTHORIZED",
            "media_rights": "REVIEW_REQUIRED",
            "visual_qa": "REVIEW_REQUIRED",
            "platform_release": "BLOCKED"
        }
    }


def connection(db_path):
    dest = Path(db_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dest))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    return conn


def store_plan(conn, plan):
    """Insert-only; never overwrite already approved/edited records."""
    packed = json.dumps(plan, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(packed.encode("utf-8")).hexdigest()
    existing = conn.execute("SELECT plan_hash FROM episodes WHERE id=?",
                            (plan["id"],)).fetchone()
    if existing:
        if existing[0] != digest:
            raise LongformError("Plan ID collision or revised plan: create a new version")
        return False
    with conn:
        conn.execute(
            "INSERT INTO episodes VALUES (?,?,?,?,?,?,?,?)",
            (plan["id"], plan["title"], plan["brief"], plan["seconds"],
             plan["ratio"], plan["schema"], plan["status"], digest)
        )
        for scene in plan["scenes"]:
            conn.execute("INSERT INTO scenes VALUES (?,?,?,?,?,?)",
                         (scene["id"], plan["id"], scene["chapter_no"],
                          scene["scene_no"], scene["beat"], scene["seconds"]))
            for j, shot in enumerate(scene["shots"], 1):
                conn.execute("INSERT INTO shots VALUES (?,?,?,?,?,?)",
                             (shot["id"], scene["id"], j, shot["seconds"],
                              shot["visual_prompt"], shot["status"]))
    return True


def public_https(url):
    """Validate syntax only; server/provider must also resolve and block private IPs."""
    if not isinstance(url, str) or len(url) > 2048:
        raise LongformError("Asset URL must be HTTPS")
    v = urlsplit(url)
    if v.scheme != "https" or not v.hostname or v.username or v.password or v.port not in (None, 443):
        raise LongformError("Asset URL must be public HTTPS without credentials")
    host = v.hostname.lower().rstrip(".")
    if (host == "localhost" or host.endswith((".local", ".internal", ".localhost"))
            or host.endswith(".test") or "." not in host):
        raise LongformError("Local/unknown asset host rejected")
    try:
        ipaddress.ip_address(host)
        raise LongformError("IP literals rejected for external renderer")
    except ValueError:
        pass
    if v.fragment:
        raise LongformError("Asset URL fragments not allowed")
    return url


def attach_asset(conn, shot_id, kind, url, rights_ref, sha256=None):
    if kind not in ("image", "video"):
        raise LongformError("Asset kind must be image or video")
    if not isinstance(rights_ref, str) or len(rights_ref.strip()) < 4:
        raise LongformError("Evidence for asset usage rights is required")
    if sha256 is not None and (
        len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256.lower())
    ):
        raise LongformError("Invalid SHA256")
    public_https(url)
    found = conn.execute("SELECT id FROM shots WHERE id=?", (shot_id,)).fetchone()
    if not found:
        raise LongformError("Unknown shot id")
    old = conn.execute("SELECT kind,source_url,rights_ref,sha256 FROM assets WHERE shot_id=?",
                       (shot_id,)).fetchone()
    new = (kind, url, rights_ref.strip(), sha256)
    if old and old != new:
        raise LongformError("Immutable asset binding; create a revised production version")
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO assets VALUES (?,?,?,?,?,?)",
            (shot_id, kind, url, rights_ref.strip(), sha256, "RIGHTS_REVIEWED")
        )
    return True


def load_timeline(conn, episode_id):
    ep = conn.execute("SELECT seconds,ratio,status FROM episodes WHERE id=?",
                      (episode_id,)).fetchone()
    if not ep:
        raise LongformError("Unknown episode")
    records = conn.execute("""
        SELECT s.id, s.scene_no, s.seconds, h.id, h.shot_no,
               h.seconds, a.kind, a.source_url, a.rights_ref
        FROM scenes s JOIN shots h ON h.scene_id=s.id
        LEFT JOIN assets a ON a.shot_id=h.id
        WHERE s.episode_id=?
        ORDER BY s.scene_no,h.shot_no
    """, (episode_id,)).fetchall()
    if not records or any(row[6] is None for row in records):
        raise LongformError("Every shot requires rights-reviewed media before render export")
    scenes = []
    for sid, scene_no, scene_sec, shot_id, shot_no, shot_sec, kind, url, rights in records:
        if not scenes or scenes[-1]["id"] != sid:
            scenes.append({"id": sid, "seconds": scene_sec, "shots": []})
        scenes[-1]["shots"].append({
            "id": shot_id, "seconds": shot_sec,
            "kind": kind, "url": public_https(url), "rights_ref": rights
        })
    if sum(s["seconds"] for s in scenes) != ep[0]:
        raise LongformError("Episode duration mismatch")
    for s in scenes:
        if sum(x["seconds"] for x in s["shots"]) != s["seconds"]:
            raise LongformError("Scene duration mismatch")
    return {"id": episode_id, "seconds": ep[0], "ratio": ep[1], "scenes": scenes}


def build_render_payload(timeline, provider):
    if provider == "shotstack":
        offset, clips = 0, []
        for scene in timeline["scenes"]:
            for shot in scene["shots"]:
                clips.append({
                    "asset": {"type": shot["kind"], "src": shot["url"]},
                    "start": offset, "length": shot["seconds"], "fit": "contain"
                })
                offset += shot["seconds"]
        return {
            "timeline": {"tracks": [{"clips": clips}]},
            "output": {"format": "mp4", "resolution": "hd",
                       "aspectRatio": timeline["ratio"]}
        }
    if provider == "json2video":
        scenes = []
        for scene in timeline["scenes"]:
            offset, elements = 0, []
            for shot in scene["shots"]:
                elements.append({
                    "type": shot["kind"], "src": shot["url"], "start": offset,
                    "duration": shot["seconds"]
                })
                offset += shot["seconds"]
            scenes.append({"duration": scene["seconds"], "elements": elements})
        return {"resolution": "full-hd", "scenes": scenes}
    raise LongformError("Unknown renderer; choose shotstack or json2video")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Long-form OneFlow offline planning and render-export")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--title", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--seconds", type=int, default=420)
    p.add_argument("--ratio", default="16:9")
    p.add_argument("--db", required=True)
    p.add_argument("--out", required=True)
    b = sub.add_parser("bind")
    b.add_argument("--db", required=True)
    b.add_argument("--shot-id", required=True)
    b.add_argument("--kind", choices=["image","video"], required=True)
    b.add_argument("--url", required=True)
    b.add_argument("--rights-ref", required=True)
    e = sub.add_parser("export")
    e.add_argument("--db", required=True)
    e.add_argument("--episode-id", required=True)
    e.add_argument("--provider", choices=["shotstack","json2video"], required=True)
    e.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            plan = make_plan(args.title, args.brief, args.seconds, args.ratio)
            with connection(args.db) as conn:
                store_plan(conn, plan)
            dest = Path(args.out)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            print("OFFLINE_ONLY " + plan["id"] + " shots=" + str(plan["shots_count"]))
        elif args.action == "bind":
            with connection(args.db) as conn:
                attach_asset(conn, args.shot_id, args.kind, args.url, args.rights_ref)
            print("RIGHTS_REVIEWED_ASSET_BOUND")
        elif args.action == "export":
            with connection(args.db) as conn:
                payload = build_render_payload(load_timeline(conn, args.episode_id), args.provider)
            dest = Path(args.out)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print("OFFLINE_RENDER_PAYLOAD_NO_PAID_TASK")
        return 0
    except LongformError as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
