#!/usr/bin/env bash
# Stable Video Infinity 2.0 (Wan 2.2) installer for an OWNED, authorized Runpod GPU.
# "source" installs only pinned repository source, WITHOUT GPU, weights, paid API calls.
# "runtime" and "weights" require explicit approval; never run automatically.
set -euo pipefail

MODE="${1:-source}"
SVI_REPO="https://github.com/vita-epfl/Stable-Video-Infinity.git"
SVI_BRANCH="svi_wan22"
SVI_REV="bab066229ea530a09587bed52c41ed6089bd509f"
SVI_HOME="${SVI_HOME:-/workspace/Stable-Video-Infinity-svi_wan22}"
SVI_VENV="${SVI_VENV:-/workspace/venvs/svi-wan22}"
PYTHON_BIN="${PYTHON_BIN:-python3.10}"

die() { printf 'SVI_INSTALL_BLOCKED: %s\n' "$*" >&2; exit 2; }
have() { command -v "$1" >/dev/null 2>&1; }
approved_gpu() {
  [[ "${SVI_APPROVE_GPU_BILLING:-0}" == "1" ]] || die "GPU billing not approved; SVI_APPROVE_GPU_BILLING=1 required"
  have nvidia-smi || die "NVIDIA driver missing; use your authorized GPU Pod"
  nvidia-smi -L
}
preflight_source() {
  have git || die "git unavailable"
  [[ "$SVI_HOME" = /* ]] || die "SVI_HOME must be an absolute path"
  [[ "$SVI_HOME" != "/" ]] || die "Refusing root as install directory"
  if [[ ! -d "$SVI_HOME/.git" ]]; then
    [[ ! -e "$SVI_HOME" ]] || die "Target exists without expected .git: $SVI_HOME"
    mkdir -p "$(dirname "$SVI_HOME")"
    git clone --depth 1 --single-branch --branch "$SVI_BRANCH" "$SVI_REPO" "$SVI_HOME"
  fi
  actual="$(git -C "$SVI_HOME" rev-parse HEAD)"
  [[ "$actual" == "$SVI_REV" ]] || die "Pinned upstream commit mismatch: $actual (expected $SVI_REV); do not silently install changed code"
  [[ "$(git -C "$SVI_HOME" remote get-url origin)" == "$SVI_REPO" ]] || die "Unexpected upstream remote"
  [[ -f "$SVI_HOME/pyproject.toml" && -f "$SVI_HOME/inference_svi_2.0.py" && -f "$SVI_HOME/LICENSE" ]] || die "SVI upstream layout mismatch"
  grep -q 'MIT License' "$SVI_HOME/LICENSE" || die "Code license changed"
  printf 'SVI_SOURCE_VERIFIED branch=%s commit=%s\n' "$SVI_BRANCH" "$actual"
}
source_install() {
  preflight_source
  if [[ "${SVI_SOURCE_EDITABLE:-0}" == "1" ]]; then
    have "$PYTHON_BIN" || die "Python 3.10 binary missing"
    "$PYTHON_BIN" -m pip install --no-deps --no-build-isolation -e "$SVI_HOME"
    "$PYTHON_BIN" -m pip show diffsynth >/dev/null || die "Editable upstream source not installed"
    echo "SVI_SOURCE_EDITABLE_INSTALLED_WITHOUT_RUNTIME_DEPENDENCIES"
  fi
}
runtime_install() {
  approved_gpu
  preflight_source
  have "$PYTHON_BIN" || die "Python 3.10 required; prepare a compatible Runpod image"
  have nvcc || die "CUDA toolkit nvcc required for upstream flash-attn build"
  [[ "$SVI_VENV" = /* && "$SVI_VENV" != "/" ]] || die "SVI_VENV must be absolute"
  "$PYTHON_BIN" -m venv "$SVI_VENV"
  "$SVI_VENV/bin/python" -m pip install --upgrade pip setuptools wheel
  "$SVI_VENV/bin/python" -m pip install \
    torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
    --index-url https://download.pytorch.org/whl/cu128
  "$SVI_VENV/bin/python" -m pip install -e "$SVI_HOME"
  "$SVI_VENV/bin/python" -m pip install --no-build-isolation flash_attn==2.8.0.post2
  "$SVI_VENV/bin/python" -m pip install 'huggingface_hub[cli]'
  "$SVI_VENV/bin/python" - <<'PY'
import torch
if not torch.cuda.is_available():
    raise SystemExit("CUDA not available; full SVI runtime NOT installed")
print("SVI_RUNTIME_DEPENDENCIES_OK torch=", torch.__version__,
      "cuda=", torch.version.cuda, "gpu=", torch.cuda.get_device_name(0))
PY
  echo "SVI_RUNTIME_INSTALLED_WEIGHTS_NOT_DOWNLOADED"
}
model_download() {
  approved_gpu
  [[ "${SVI_APPROVE_DOWNLOAD:-0}" == "1" ]] || die "Explicit large-model download approval required"
  [[ "${SVI_MODEL_LICENSE_CHECKED:-0}" == "1" ]] || die "Base Wan and SVI LoRA license review required"
  preflight_source
  [[ -x "$SVI_VENV/bin/python" ]] || die "Run runtime installation first"
  SVI_HOME="$SVI_HOME" "$SVI_VENV/bin/python" - <<'PY'
import os, shutil
home = os.environ["SVI_HOME"]
free = shutil.disk_usage(home).free / 2**30
print(f"SVI model storage free = {free:.1f} GiB")
if free < 180:
    raise SystemExit("Need at least 180 GiB free for base model + downloads + cache before downloading")
PY
  # This operation downloads potentially many GiB. DO NOT schedule unless explicitly authorized.
  SVI_HOME="$SVI_HOME" "$SVI_VENV/bin/python" - <<'PY'
import os
from huggingface_hub import snapshot_download
home = os.environ["SVI_HOME"]
token = os.environ.get("HF_TOKEN") or None
snapshot_download(repo_id="Wan-AI/Wan2.2-I2V-A14B",
                  local_dir=os.path.join(home,"models/Wan-AI/Wan2.2-I2V-A14B"),
                  token=token)
snapshot_download(repo_id="vita-video-gen/svi-model",
                  allow_patterns=[
                    "version-2.0/SVI_Wan2.2-I2V-A14B_high_noise_lora_v2.0.safetensors",
                    "version-2.0/SVI_Wan2.2-I2V-A14B_low_noise_lora_v2.0.safetensors"],
                  local_dir=os.path.join(home,"models/Stable-Video-Infinity"),
                  token=token)
print("SVI_WAN22_WEIGHT_DOWNLOAD_COMPLETED_INFERENCE_NOT_YET_VALIDATED")
PY
}
case "$MODE" in
  source) source_install ;;
  runtime) runtime_install ;;
  weights) model_download ;;
  *) die "Supported modes: source|runtime|weights" ;;
esac
