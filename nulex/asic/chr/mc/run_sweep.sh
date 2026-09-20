#!/bin/bash
# th22 C-element Monte-Carlo Vt-mismatch sweep over mismatch magnitude (kvt).
# Requires the PyMS-fixed Xyce (PSP103 via .hdl JIT) with the runtime-callback
# param path: PYMS_CALLBACK_PARAMS=DELVTO keeps DELVTO symbolic in the .so and
# fetched live, so all 200 per-device-DELVTO samples (and every kvt) share ONE
# .so per transistor geometry (4 builds total). Without the callback, .SAMPLING
# would silently reuse the first sample's baked DELVTO (no variation).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
export PYMS_DIR="${PYMS_DIR:-/usr/local/share/xyce/PyMS}"
export PYMS_CALLBACK_PARAMS=DELVTO
XYCE="${XYCE:-/usr/local/src/xyce-build/src/Xyce}"
N="${N:-200}"
OUT="${OUT:-$HERE/out}"; mkdir -p "$OUT"; cd "$OUT"
for KVT in "${@:-1 2 3 4}"; do
  D="$OUT/mc_k${KVT}.cir"
  sed -e "s/__KVT__/${KVT}/" -e "s/__N__/${N}/" "$HERE/mc_th22.cir" > "$D"
  cp "$HERE/th22_mc.sp" "$OUT/th22_mc.sp"
  echo "===== kvt=${KVT} N=${N} ====="
  "$XYCE" "$D" > "$OUT/mc_k${KVT}.log" 2>&1
  echo "  exit $?  (.so builds: run with a fresh PYMS_VAE_CACHE to count)"
done
python3 "$HERE/analyze_mc.py" "$OUT"/mc_k*.cir
