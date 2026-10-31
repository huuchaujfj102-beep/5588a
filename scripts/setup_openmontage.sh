#!/usr/bin/env bash
# Repeatable, isolated OpenMontage installation for 5588a.
# Upstream source stays outside tracked files, pinned to a reviewed commit.
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPENMONTAGE_REF="${OPENMONTAGE_REF:-195eab24478dc9363326aec437aefc3701635ddf}"
OPENMONTAGE_HOME="${OPENMONTAGE_HOME:-${PROJECT_ROOT}/.local/openmontage}"

for program in git make python3 node npm ffmpeg ffprobe; do
  command -v "$program" >/dev/null 2>&1 || { echo "Missing required program: $program" >&2; exit 1; }
done

if [[ -e "$OPENMONTAGE_HOME" && ! -d "$OPENMONTAGE_HOME/.git" ]]; then
  echo "Refusing to overwrite a non-git directory: $OPENMONTAGE_HOME" >&2
  exit 1
fi
if [[ ! -d "$OPENMONTAGE_HOME/.git" ]]; then
  mkdir -p "$(dirname "$OPENMONTAGE_HOME")"
  git clone --filter=blob:none --no-checkout https://github.com/calesthio/OpenMontage.git "$OPENMONTAGE_HOME"
fi
git -C "$OPENMONTAGE_HOME" fetch --depth=1 origin "$OPENMONTAGE_REF"
git -C "$OPENMONTAGE_HOME" checkout --detach "$OPENMONTAGE_REF"

echo "OpenMontage source revision: $(git -C "$OPENMONTAGE_HOME" rev-parse HEAD)"
echo "Installing Python/Node/Remotion/Piper dependencies without any paid API keys..."
make -C "$OPENMONTAGE_HOME" setup
echo "Running offline provider preflight..."
make -C "$OPENMONTAGE_HOME" preflight
echo "OpenMontage installation and preflight completed: $OPENMONTAGE_HOME"
