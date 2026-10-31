#!/usr/bin/env bash
# Run inside a user-owned Runpod GPU Pod. Never run on GitHub Actions.
set -euo pipefail

WAN_HOME="${WAN_HOME:-/workspace/Wan2.2}"
MODEL_HOME="${MODEL_HOME:-/workspace/models/Wan2.2-TI2V-5B}"
WAN_REV="1ea34ff48f87168174e12956e200b1d908b1c5ff"
HF_MODEL_ID="Wan-AI/Wan2.2-TI2V-5B"

command -v git >/dev/null || { echo "git required" >&2; exit 1; }
command -v nvidia-smi >/dev/null || { echo "Run this only on a GPU Pod with NVIDIA drivers" >&2; exit 1; }
command -v python >/dev/null || { echo "python missing" >&2; exit 1; }
nvidia-smi
python - <<'PY'
import shutil
free = shutil.disk_usage('/workspace').free / (1024**3)
print(f"Available /workspace storage: {free:.1f} GiB")
if free < 70:
    raise SystemExit("At least 70 GiB free is recommended before installing/downloading the checkpoint")
PY
if [ ! -d "$WAN_HOME/.git" ]; then
  git clone https://github.com/Wan-Video/Wan2.2.git "$WAN_HOME"
fi
git -C "$WAN_HOME" fetch --depth 1 origin "$WAN_REV"
git -C "$WAN_HOME" checkout --detach "$WAN_REV"
test "$(git -C "$WAN_HOME" rev-parse HEAD)" = "$WAN_REV"

python -m pip install -r "$WAN_HOME/requirements.txt"
python -m pip install "huggingface_hub[cli]"
python - <<'PY'
import torch
if not torch.cuda.is_available():
    raise SystemExit("PyTorch CUDA is unavailable; choose a compatible Runpod image")
print(f"Torch {torch.__version__}, CUDA {torch.version.cuda}")
if torch.cuda.get_device_properties(0).total_memory / (1024**3) < 23.0:
    raise SystemExit("Wan TI2V-5B requires a GPU with at least 24 GB nominal VRAM")
PY
if [ "${WAN_DOWNLOAD:-0}" = "1" ]; then
  MODEL_HOME="$MODEL_HOME" HF_MODEL_ID="$HF_MODEL_ID" python - <<'PY'
import os
from huggingface_hub import snapshot_download
snapshot_download(
  repo_id=os.environ["HF_MODEL_ID"],
  local_dir=os.environ["MODEL_HOME"],
)
print("Checkpoint download complete; inference has NOT been verified")
PY
else
  echo "Environment installed; checkpoint not downloaded. Rerun with WAN_DOWNLOAD=1 to download the large model."
fi
echo "Bootstrap completed. Run a one-shot smoke test with python -m runpod_wan.smoke from this repo."
