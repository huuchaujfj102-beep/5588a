"""Nodaro free-tier 4+4+4+2s I2V connector for OneFlow.
Plan is offline. Rendering requires explicit --live, secret API token and verified
per-clip price keys. Never merges to main or publishes media automatically.
"""
import argparse
import json
import os
import pathlib
import subprocess
import time
import urllib.parse
import urllib.request
import uuid

BASE = "https://app.nodaro.ai"
MODEL = "seedance-2-fast"
DURATIONS = (4, 4, 4, 2)
LOCK = ("Continue the exact same silver-white, low-profile bio-organic supercar "
        "with transparent jade leaf-vein panels, jade neural lights, large original "
        "turbine wheels, cream seats, golden alpine lake, curved glass architecture, "
        "wet stone and waterfall; preserve exact geometric identity and geography. "
        "Realistic camera physics, 24fps cinematic look, no new parts, no warping, "
        "no melted surroundings, no extra wheels, no subtitles.")
SHOTS = (
    "From the genuine previous film end frame, close front 45-degree angle; intensified micro emerald nerve pulses; subtle chassis compression, gradual wheel pre-start; very slow stable dolly.",
    "Detailed low-angle front-wheel launch: realistic torque, tire contact and wet stone spray; the car drives FORWARD onto a plausible connected lakeside driveway without flying.",
    "Elegant very low side-rear chase along same lake; physically coherent glass architecture and waterfall reflections; fast internal emerald light and thin subtle jade photon trail, not thick neon.",
    "Crane to elevated rear three-quarter sunset view; identical car follows lakeside curve, fine emerald wake fades, final half-second steady and sharp."
)


class Blocked(RuntimeError):
    pass


def plan():
    return {"schema": "oneflow.nodaro-trial.v1", "duration": 14, "fps": 24,
            "ratio": "4:3", "source": "REAL final frame of supplied 13.75s clip",
            "status": "PLAN_NOT_RENDERED", "publish_approved": False,
            "shots": [{"id": "S%02d" % (i+1), "start": sum(DURATIONS[:i]),
                       "seconds": sec, "resolution": "480p", "model": MODEL,
                       "prompt": LOCK + " " + SHOTS[i]}
                      for i, sec in enumerate(DURATIONS)]}


def api(path, token, data=None):
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(BASE + path, data=body,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json"}, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read(2000000))
    except Exception as exc:
        raise Blocked("Nodaro request failed (" + type(exc).__name__ + ")") from None


def quote(token, key):
    result = api("/v1/credits/model-cost?model=" + urllib.parse.quote(key, safe=""), token)
    value = result.get("data")
    if isinstance(value, dict):
        value = value.get("credits")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise Blocked("Unable to verify live price; refusing generation")
    return float(value)


def balance(token):
    result = api("/v1/credits/balance", token).get("data")
    if isinstance(result, dict):
        for key in ("total", "balance", "totalCredits", "credits"):
            value = result.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    raise Blocked("Unable to verify free credit balance")


def upload(token, file):
    blob = pathlib.Path(file).read_bytes()
    if not blob or len(blob) > 12000000:
        raise Blocked("Reference image invalid or over 12MB")
    boundary = "OneFlow" + uuid.uuid4().hex
    filename = pathlib.Path(file).name
    if pathlib.Path(file).suffix.lower() not in (".jpg", ".jpeg", ".png"):
        raise Blocked("Reference must be JPG or PNG")
    mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    body = (("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + filename
            + "\"\r\nContent-Type: " + mime + "\r\n\r\n").encode() + blob
            + ("\r\n--" + boundary + "\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\nimage"
               "\r\n--" + boundary + "--\r\n").encode())
    request = urllib.request.Request(BASE + "/v1/upload", data=body, method="POST",
         headers={"Authorization": "Bearer " + token,
                  "Content-Type": "multipart/form-data; boundary=" + boundary})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            url = json.load(response).get("data", {}).get("url")
    except Exception as exc:
        raise Blocked("Media upload failed (" + type(exc).__name__ + ")") from None
    if not isinstance(url, str) or not url.startswith("https://"):
        raise Blocked("Media upload returned no HTTPS URL")
    return url


def ffmpeg(*args):
    try:
        subprocess.run(("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str,args)),
                       check=True, timeout=900)
    except (OSError, subprocess.SubprocessError):
        raise Blocked("FFmpeg failed") from None


def download(url, target):
    p = urllib.parse.urlparse(url)
    if p.scheme != "https" or not p.hostname or p.hostname in ("localhost", "127.0.0.1"):
        raise Blocked("Video result URL is not approved HTTPS")
    with urllib.request.urlopen(url, timeout=180) as response, open(target, "wb") as output:
        total = 0
        while True:
            block = response.read(1024*1024)
            if not block:
                break
            total += len(block)
            if total > 250000000:
                raise Blocked("Generated video exceeds 250MB")
            output.write(block)
    if os.path.getsize(target) < 4096:
        raise Blocked("Downloaded video is invalid")


def run(args):
    token = os.getenv("NODARO_API_KEY")
    if not token:
        raise Blocked("NODARO_API_KEY missing: configure GitHub secret or environment")
    if not args.confirm_free_credits or args.credit_cap is None or args.credit_cap <= 0:
        raise Blocked("Explicit free-credit confirmation and positive credit cap required")
    if not args.price_key_4 or not args.price_key_2:
        raise Blocked("Verified model price IDs for 4s and 2s are required")
    start = pathlib.Path(args.start_frame)
    if not start.is_file():
        raise Blocked("Source video LAST FRAME is not available")
    p4 = quote(token, args.price_key_4)
    p2 = quote(token, args.price_key_2)
    total = p4*3 + p2
    if total > args.credit_cap or total > balance(token):
        raise Blocked("Credit quote exceeds cap or balance: 0 generations started")
    output = pathlib.Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    record = plan()
    record["status"] = "GENERATING_NOT_APPROVED"
    record["quoted_credits"] = total
    clips = []
    for i, shot in enumerate(record["shots"]):
        if balance(token) < (p2 if shot["seconds"] == 2 else p4):
            raise Blocked("Not enough credits for next shot; stopping without resubmitting")
        url = upload(token, start)
        result = api("/v1/generate-video", token,
            {"imageUrl": url, "provider": MODEL, "prompt": shot["prompt"],
             "duration": shot["seconds"], "resolution": "480p", "aspectRatio": "4:3",
             "generateAudio": False})
        job_id = result.get("jobId")
        if not isinstance(job_id, str) or not job_id:
            raise Blocked("No job ID; outcome unknown, do not retry automatically")
        shot["job_id"] = job_id
        (output/"manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
        for attempt in range(180):
            state = api("/v1/jobs/" + urllib.parse.quote(job_id, safe="") + "/status",
                        token).get("data", {})
            if state.get("status") in ("completed", "failed", "cancelled"):
                break
            time.sleep(5)
        if state.get("status") != "completed":
            raise Blocked("Job not completed: " + job_id)
        video_url = (state.get("output_data") or {}).get("videoUrl")
        if not video_url:
            raise Blocked("Job returned no video: " + job_id)
        path = output/("S%02d.mp4" % (i+1))
        download(video_url, path)
        clips.append(path)
        start = output/("S%02d_last.jpg" % (i+1))
        ffmpeg("-sseof", "-0.05", "-i", path, "-frames:v", 1, start)
        if not start.is_file():
            raise Blocked("Cannot extract next start frame")
    inputs = [arg for file in clips for arg in ("-i", str(file))]
    parts = []
    for i, sec in enumerate(DURATIONS):
        parts.append("[%d:v]trim=duration=%d,setpts=PTS-STARTPTS,fps=24,"
                     "scale=1024:768:force_original_aspect_ratio=decrease,"
                     "pad=1024:768:(ow-iw)/2:(oh-ih)/2,setsar=1[v%d]" % (i, sec, i))
    parts.append("".join("[v%d]" % i for i in range(4)) + "concat=n=4:v=1:a=0[v]")
    ffmpeg(*inputs, "-filter_complex", ";".join(parts), "-map", "[v]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", output/"roughcut_14s.mp4")
    record["status"] = "ROUGH_CUT_REQUIRES_VISUAL_AUDIO_LICENSE_QC"
    (output/"manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2))
    print(str(output/"roughcut_14s.mp4"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    p.add_argument("--start-frame", default="")
    p.add_argument("--output", default="output/nodaro_trial")
    p.add_argument("--confirm-free-credits", action="store_true")
    p.add_argument("--credit-cap", type=float)
    p.add_argument("--price-key-4")
    p.add_argument("--price-key-2")
    args = p.parse_args()
    if args.live:
        run(args)
    else:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Blocked as exc:
        print("BLOCKED: " + str(exc))
        raise SystemExit(2)
