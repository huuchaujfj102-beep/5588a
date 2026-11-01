"""Magic Hour trial I2V candidate for OneFlow.

This adapter is inert by default. Live calls require an actual API token and
an account-specific quoted cost, capped using the account's available credits.
Trial outputs are for NONCOMMERCIAL evaluation unless rights are upgraded.
"""
import argparse
import json
import os
import pathlib
import urllib.request


class TrialBlocked(RuntimeError):
    pass


def plan():
    return {
        "provider": "magic-hour",
        "status": "PREPARED_NOT_AUTHORIZED_NOT_RENDERED",
        "duration_seconds": 14,
        "resolution": "480p",
        "reference": "real final frame from 13.75s source car video",
        "license_gate": "FREE_TRIAL_NONCOMMERCIAL_REVIEW_ONLY",
        "billing_gate": "explicit account credit quote + user-entered cap",
        "prompt": (
            "Seamless 14-second cinematic continuation from the source final image. "
            "PRESERVE THE EXACT ORIGINAL silver-white concept hypercar with translucent "
            "jade-green biological leaf-vein shell, large turbine-like wheels and cream seats; "
            "keep golden mountain lake, white organic glass architecture, waterfall and geography. "
            "0-2.5s close front angle: delicate emerald neural pulses and controlled headlight "
            "intensity, gentle physical suspension compression. 2.5-5s wheel close-up: accurate "
            "tire acceleration, tiny spray from wet stone, vehicle drives FORWARD onto a real "
            "connected lakeside lane. 5-9s low rear-side tracking shot: high-speed graceful "
            "acceleration, sharp real optical reflections of buildings and trees. 9-12s "
            "ultra-thin jade photon trails from the existing body, atmospheric refraction, "
            "premium realistic aerodynamic motion, no rocket thrusters. 12-14s elevated "
            "rear-three-quarter view of same car receding along lake curve in golden sunset, "
            "stable final half-second. No body deformation, no extra wheels, no flying car, "
            "no scene reset, no new external body parts, no water or background melting, "
            "no blown-out neon or cartoonish lasers, no narration, realistic sound design."
        )
    }


def available_credits(key):
    request = urllib.request.Request("https://api.magichour.ai/v1/account",
            headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(request, timeout=30) as res:
            record = json.load(res)
    except Exception as exc:
        raise TrialBlocked("Cannot verify Magic Hour account credits") from None
    data = record.get("data", record)
    if isinstance(data, dict):
        for field in ("credits", "available_credits", "availableCredits", "credit_balance"):
            value = data.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
                return float(value)
    raise TrialBlocked("Account returned no safely parseable credit total")


def live(args):
    key = os.environ.get("MAGIC_HOUR_API_KEY")
    if not key:
        raise TrialBlocked("MAGIC_HOUR_API_KEY not connected")
    if not args.source_frame or not pathlib.Path(args.source_frame).is_file():
        raise TrialBlocked("Actual previous film last frame not found")
    if not args.confirm_trial_credits or args.quoted_credits is None or args.credit_cap is None:
        raise TrialBlocked("Quote, credit cap and explicit consent are required")
    if args.quoted_credits <= 0 or args.quoted_credits > args.credit_cap:
        raise TrialBlocked("Quoted generation exceeds approved maximum")
    if available_credits(key) < args.quoted_credits:
        raise TrialBlocked("Free/trial account credits are insufficient")
    try:
        from magic_hour import Client
    except ImportError:
        raise TrialBlocked("Install official SDK: pip install magic_hour") from None
    outdir = pathlib.Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    brief = plan()
    # Exactly one generation; on unknown timeouts, check existing project before retrying.
    response = Client(token=key).v1.image_to_video.generate(
        name="APEX MOTION Emerald 14s trial continuation",
        assets={"image_file_path": str(pathlib.Path(args.source_frame).resolve())},
        end_seconds=14.0,
        resolution="480p",
        model="ltx-2.5",
        style={"prompt": brief["prompt"]},
        wait_for_completion=True,
        download_outputs=True,
        download_directory=str(outdir)
    )
    print(json.dumps({"status": "RENDER_RETURNED_NOT_LICENSED_OR_VISUALLY_APPROVED",
                      "provider_result": str(response)[:1500],
                      "output_dir": str(outdir), "publish_approved": False}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--source-frame")
    parser.add_argument("--output", default="output/magic_hour_trial")
    parser.add_argument("--quoted-credits", type=float)
    parser.add_argument("--credit-cap", type=float)
    parser.add_argument("--confirm-trial-credits", action="store_true")
    args = parser.parse_args()
    if not args.live:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return
    live(args)


if __name__ == "__main__":
    try:
        main()
    except TrialBlocked as exc:
        print("BLOCKED: " + str(exc))
        raise SystemExit(2)
