"""Read-only SVI Wan2.2 installation inspection. Never download model or run inference."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

REV="bab066229ea530a09587bed52c41ed6089bd509f"
HIGH="SVI_Wan2.2-I2V-A14B_high_noise_lora_v2.0.safetensors"
LOW="SVI_Wan2.2-I2V-A14B_low_noise_lora_v2.0.safetensors"


def inspect(home: Path, venv: Path):
    home=home.expanduser().resolve()
    venv=venv.expanduser().resolve()
    source=(home / "inference_svi_2.0.py").is_file()
    git_verified=False
    if source and (home / ".git").is_dir() and shutil.which("git"):
        result=subprocess.run(["git","-C",str(home),"rev-parse","HEAD"],
                              capture_output=True,text=True,timeout=15,check=False)
        git_verified=result.returncode==0 and result.stdout.strip()==REV
    runtime=(venv / "bin/python").is_file()
    loras=home / "models" / "Stable-Video-Infinity" / "version-2.0"
    high=(loras / HIGH).is_file()
    low=(loras / LOW).is_file()
    base=home / "models" / "Wan-AI" / "Wan2.2-I2V-A14B"
    base_present=base.is_dir() and any(base.rglob("*.safetensors"))
    gpu=bool(shutil.which("nvidia-smi"))
    free_gib=round(shutil.disk_usage(home if home.is_dir() else home.parent).free/(1024**3),1) if home.parent.is_dir() else None
    return {
      "source_checked":git_verified,
      "python_runtime_venv_exists":runtime,
      "svi_lora_high_present":high,
      "svi_lora_low_present":low,
      "wan22_A14B_files_present":base_present,
      "nvidia_smi_available":gpu,
      "storage_free_gib":free_gib,
      "real_gpu_inference_verified":False,
      "model_licenses_approved":False,
      "overall":"MODEL_READY_FOR_GPU_SMOKE_ONLY" if all([git_verified,runtime,high,low,base_present,gpu]) else "INCOMPLETE"
    }


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--home",default="/workspace/Stable-Video-Infinity-svi_wan22")
    p.add_argument("--venv",default="/workspace/venvs/svi-wan22")
    args=p.parse_args(argv)
    print(json.dumps(inspect(Path(args.home),Path(args.venv)),ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
