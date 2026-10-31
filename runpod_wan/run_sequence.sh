#!/usr/bin/env bash
# Intended for a user-owned Runpod GPU Pod registered as a GitHub self-hosted runner.
# Order is enforced: bootstrap -> dry-run -> paid GPU inference -> ffprobe JSON.
set -euo pipefail

if [[ "${WAN_CONFIRM_GPU_COST:-}" != "true" ]]; then
  echo "BLOCKED: user must explicitly opt in to paid GPU execution." >&2
  exit 2
fi

if [[ ! -d /workspace ]] || ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "BLOCKED: this job requires a real, accessible Runpod NVIDIA GPU Pod." >&2
  exit 3
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n "${WAN_ONE_SENTENCE:-}" ]]; then
  if [[ ${#WAN_ONE_SENTENCE} -gt 6000 ]]; then
    echo "BLOCKED: one-sentence brief exceeds 6000 characters." >&2
    exit 4
  fi
  PROMPT_FILE="${RUNNER_TEMP:-/tmp}/wan22-brief.txt"
  printf '%s\n' "$WAN_ONE_SENTENCE" > "$PROMPT_FILE"
else
  PROMPT_FILE="runpod_wan/sample_snow_white_S01.txt"
fi

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "BLOCKED: prompt file missing." >&2
  exit 5
fi

SHOT_TAG="${GITHUB_RUN_ID:-manual}-${GITHUB_RUN_ATTEMPT:-1}"
OUTPUT_DIR="/workspace/oneflow-output"
mkdir -p "$OUTPUT_DIR"
OUTPUT="$OUTPUT_DIR/snow-white-S01-${SHOT_TAG}.mp4"

echo "1/3 bootstrap Wan2.2 & approved checkpoint onto this GPU Pod"
WAN_DOWNLOAD=1 bash runpod_wan/bootstrap.sh

echo "2/3 verify live Pod files and exact Wan command without inference charges"
python -m runpod_wan.smoke \
  --prompt-file "$PROMPT_FILE" \
  --output "$OUTPUT" \
  --seconds 5 --seed 128839 --dry-run

echo "3/3 explicitly authorized 5-second GPU generation"
python -m runpod_wan.smoke \
  --prompt-file "$PROMPT_FILE" \
  --output "$OUTPUT" \
  --seconds 5 --seed 128839 --confirm-gpu-spend

test -s "$OUTPUT"
test -s "${OUTPUT%.mp4}.audit.json"

echo "SUCCESS: real video verified by ffprobe; still requires human visual review"
echo "Output remains private in Runpod persistent volume: $OUTPUT"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    echo "## Wan2.2 5-second test"
    echo ""
    echo "**Status:** GPU_RENDERED_REVIEW_REQUIRED"
    echo ""
    echo "**Runpod private output:** \`$OUTPUT\`"
    echo ""
    echo "The MP4 is **not** published to this public GitHub repository."
    echo "Audio, visual fidelity, permissions and continuity still require separate review."
  } >> "$GITHUB_STEP_SUMMARY"
fi
