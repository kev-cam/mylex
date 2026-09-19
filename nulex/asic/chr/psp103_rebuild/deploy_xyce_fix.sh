#!/bin/bash
# Deploy the already-built, guard-fixed Xyce over the stale /usr/local install.
#
# Root cause: commit 669e3b75 (2026-06-22) "DeviceMgr: guard undefined model_group
# type_index (fixes dynamic-device instantiation SIGSEGV)" fixed the crash that hits
# every dynamically-registered PyMS/ADMS device (e.g. PSP103) at topology setup.
# It was rebuilt into /usr/local/src/xyce-build (2026-07-09) but never installed:
# /usr/local/lib/libXyceLib.so is still the pre-fix May-16 build.
#
# Verified safe: xyce-build lib has identical 27 NEEDED deps to the installed one,
# all resolving from system paths (no build-tree dependency); resistor + PSP103 both
# run to "End of Xyce" under it. This swaps the matched (lib, launcher) pair, with a
# timestamped backup so it is fully reversible.
#
# Run as:  sudo bash deploy_xyce_fix.sh
set -euo pipefail

SRC=/usr/local/src/xyce-build/src
LIB=/usr/local/lib/libXyceLib.so
BIN=/usr/local/bin/Xyce
STAMP=$(date +%Y%m%d-%H%M%S)
BAK=/usr/local/lib/xyce-preguard-backup-$STAMP

[ "$(id -u)" = 0 ] || { echo "ERROR: run with sudo"; exit 1; }
[ -f "$SRC/libXyceLib.so" ] && [ -x "$SRC/Xyce" ] || { echo "ERROR: xyce-build artifacts missing"; exit 1; }

echo "== 1. backup current install -> $BAK"
mkdir -p "$BAK"
cp -p "$LIB" "$BAK/libXyceLib.so"
cp -p "$BIN" "$BAK/Xyce"
echo "   backed up: $(readelf -n "$LIB" | awk '/Build ID/{print $NF}')"

echo "== 2. install guard-fixed matched pair"
install -m 0755 "$SRC/libXyceLib.so" "$LIB"
install -m 0755 "$SRC/Xyce"          "$BIN"
ldconfig
echo "   installed: $(readelf -n "$LIB" | awk '/Build ID/{print $NF}')  (expect 756bb423...)"

echo "== 3. smoke test the INSTALLED binary (fresh JIT cache)"
rm -rf /tmp/pyms_hdl_cache
TD=$(mktemp -d)
cat > "$TD/psp.cir" <<'EOF'
PSP103 smoke test via installed Xyce
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
Vd d 0 0.5
Vg g 0 1.0
Vs s 0 0
Vb b 0 0
M1 d g s b nmosmod
.model nmosmod nmos level=103
.op
.print dc v(d) i(Vd)
.end
EOF
if /usr/local/bin/Xyce "$TD/psp.cir" 2>&1 | grep -q "End of Xyce"; then
  echo "   PASS: installed Xyce runs PSP103 (no SIGSEGV)"
else
  echo "   FAIL: PSP103 still crashes -- restoring backup"
  install -m 0755 "$BAK/libXyceLib.so" "$LIB"
  install -m 0755 "$BAK/Xyce"          "$BIN"
  ldconfig
  rm -rf "$TD"; exit 1
fi
rm -rf "$TD"

echo "== 4. reset JIT cache so it rebuilds as the invoking user"
rm -rf /tmp/pyms_hdl_cache
echo "=== XYCE FIX DEPLOYED (backup: $BAK) ==="
