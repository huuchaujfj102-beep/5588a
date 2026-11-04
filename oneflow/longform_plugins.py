"""Optional local open-source plugins for longform production.

No model weights/binaries are downloaded or run just by importing this module.
Only explicit local CLI calls can execute already installed, audited tools.
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from .longform import LongformError


UPSTREAM = {
    "svi": {
        "repo": "https://github.com/vita-epfl/Stable-Video-Infinity",
        "license_note": "SVI repository MIT; base Wan weights and any LoRA separately review",
        "requirements": "Python, verified GPU, checkpoints, upstream script configuration",
        "script": "scripts/test/svi_2.0.sh",
    },
    "longcat": {
        "repo": "https://github.com/meituan-longcat/LongCat-Video",
        "license_note": "Repository MIT; verify separately downloaded checkpoints and outputs",
        "requirements": "PyTorch GPU, verified LongCat weights, model runtime",
        "script": "run_demo_long_video.py",
    },
    "rhubarb": {
        "repo": "https://github.com/DanielSWolf/rhubarb-lip-sync",
        "license_note": "MIT. Chinese narration: phonetic recognizer; inspect timing manually",
        "requirements": "Trusted rhubarb CLI binary and approved local WAV/OGG",
        "script": None,
    }
}


def local_model_command(provider, repo_dir, *, checkpoint_dir=None):
    if provider not in ("svi", "longcat"):
        raise LongformError("Only SVI and LongCat support local model launch")
    root = Path(repo_dir).resolve()
    script = root / UPSTREAM[provider]["script"]
    if not script.is_file():
        raise LongformError("Verified upstream script not installed: " + str(script))
    if provider == "svi":
        return ["bash", str(script)]
    if not checkpoint_dir or not Path(checkpoint_dir).is_dir():
        raise LongformError("LongCat checkpoints missing; no model execution")
    if shutil.which("torchrun") is None:
        raise LongformError("torchrun unavailable")
    return ["torchrun", str(script), "--checkpoint_dir", str(Path(checkpoint_dir).resolve())]


def lip_sync_command(audio, output, *, binary="rhubarb", dialog=None):
    source = Path(audio)
    if not source.is_file() or source.suffix.lower() not in (".wav", ".ogg"):
        raise LongformError("Rhubarb requires an existing WAV or OGG audio file")
    if not shutil.which(binary) and not Path(binary).is_file():
        raise LongformError("Rhubarb not installed; obtain trusted upstream CLI release")
    cmd = [binary, "-r", "phonetic", "-f", "json", "-o", str(output)]
    if dialog is not None:
        if not Path(dialog).is_file():
            raise LongformError("Dialog transcript missing")
        cmd += ["-d", str(dialog)]
    cmd.append(str(source))
    return cmd


def local_execute(command, *, cwd=None, execute=False, license_checked=False,
                  confirm_gpu_cost=False, timeout_seconds=1800):
    if not execute:
        return {"status":"PLAN_ONLY","command":command,
                "subprocess_executed":False,"provider_charged":False}
    if not license_checked or not confirm_gpu_cost:
        raise LongformError("Execution requires --license-checked and --confirm-gpu-cost")
    if timeout_seconds < 1 or timeout_seconds > 14400:
        raise LongformError("Unsafe timeout")
    try:
        result = subprocess.run(command, cwd=cwd, check=True, timeout=timeout_seconds,
                                capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise LongformError("Local model/plugin failed; inspect private logs, no blind retry") from None
    return {"status":"FINISHED_PROCESS_NOT_MEDIA_QA","returncode":result.returncode,
            "stdout_tail":result.stdout[-1500:],"subprocess_executed":True}


def main(argv=None):
    p=argparse.ArgumentParser(description="Inspect or run optional long video plugins")
    p.add_argument("--provider",choices=sorted(UPSTREAM),required=True)
    p.add_argument("--repo-dir")
    p.add_argument("--checkpoint-dir")
    p.add_argument("--audio")
    p.add_argument("--output")
    p.add_argument("--dialog")
    p.add_argument("--binary",default="rhubarb")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--license-checked",action="store_true")
    p.add_argument("--confirm-gpu-cost",action="store_true")
    args=p.parse_args(argv)
    try:
        if args.provider=="rhubarb":
            if not args.audio or not args.output:
                raise LongformError("--audio and --output required for rhubarb")
            cmd=lip_sync_command(args.audio,args.output,binary=args.binary,dialog=args.dialog)
        else:
            if not args.repo_dir:
                raise LongformError("--repo-dir required")
            cmd=local_model_command(args.provider,args.repo_dir,
                                    checkpoint_dir=args.checkpoint_dir)
        result=local_execute(cmd,cwd=args.repo_dir,execute=args.execute,
                             license_checked=args.license_checked,
                             confirm_gpu_cost=args.confirm_gpu_cost)
        print(json.dumps({"provider":args.provider,"upstream":UPSTREAM[args.provider],
                          "result":result},ensure_ascii=False,indent=2))
        return 0
    except LongformError as exc:
        p.exit(2,"BLOCKED: "+str(exc)+"\n")


if __name__=="__main__":
    raise SystemExit(main())
