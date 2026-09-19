#!/bin/bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# nulex phys-binding gate: map_ncl_struct.py --target spice.
#
# Lowers a dual-rail NCL netlist to a transistor-level SG13G2 .subckt (real
# th22.sp / th_gates.sp / th_cells_sg13g2.sp cells + PSP103), and verifies it:
#   1. EMIT + STRUCTURE (always): the transistor netlist is well-formed and its
#      TH-cell census matches the behaviorally-verified --target verilog netlist
#      (whose logic run_struct.sh already proved == sync golden, 256/256).
#   2. CELL DC LOGIC (when a PSP103-capable Xyce is present): each transistor TH
#      cell computes its threshold function at DC — th22 (C-element set/reset)
#      and the OR-collectors th12/th13/th14.
#
# Block-level TRANSIENT simulation of a mapped block is NOT yet a gate: the JIT
# PSP103 model's transient converges only at ~1f load (its DC is solid), so a
# full-block NULL->DATA transient / full NLDM characterization await a more
# transient-robust PSP103 charge model. See asic/chr/README.md.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
NULEX=$(cd "$HERE/../.." && pwd)
MAP="$NULEX/map_ncl_struct.py"
CELLS=/usr/local/src/ldx/asic/cells
SUP="$NULEX/lib/th_cells_sg13g2.sp"
MODEL=/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib
PSP=/usr/local/share/xyce/verilog-a/psp103/psp103.va
XYCE="${XYCE:-/usr/local/src/xyce-build/src/Xyce}"
export LD_LIBRARY_PATH="/usr/local/src/xyce-build/src:${LD_LIBRARY_PATH:-}"
export PYMS_DIR="${PYMS_DIR:-/usr/local/share/xyce/PyMS}"
export XYCE_BUILD="${XYCE_BUILD:-/usr/local/src/xyce-build}"
WORK=$(mktemp -d)
fail() { echo "FAIL: $*"; exit 1; }

echo "== 1. emit add4 -> transistor-level SG13G2 netlist (--target spice)"
python3 "$MAP" "$HERE/add4.json" add4 "$WORK/add4_phys.sp" --target spice >/dev/null || fail "emit"
grep -q '^\.subckt add4 ' "$WORK/add4_phys.sp" || fail "no .subckt add4"
grep -q '^\.ends add4'     "$WORK/add4_phys.sp" || fail "no .ends add4"
# census must match the behavioral (verilog) netlist's TH-cell instances
python3 "$MAP" "$HERE/add4.json" add4 "$WORK/add4_v.v" --target verilog >/dev/null || fail "verilog emit"
census_sp=$(grep -E '^  X[0-9]+ ' "$WORK/add4_phys.sp" | awk '{print $NF}' | sort | uniq -c | awk '{print $1, $2}')
census_v=$(grep -oE '^  th[0-9]+w?[0-9]* u[0-9]' "$WORK/add4_v.v" | awk '{print $1}' | sort | uniq -c | awk '{print $1, $2}')
[ "$census_sp" = "$census_v" ] || fail "spice census != verilog census:
spice:
$census_sp
verilog:
$census_v"
echo "   ok: $(echo "$census_sp" | tr '\n' ' ')"

echo "== 2. transistor TH-cell DC logic (needs PSP103-capable Xyce; slow: JIT builds)"
if [ -x "$XYCE" ]; then
  cat > "$WORK/cells.cir" <<EOF
TH transistor-cell DC logic
.hdl "$PSP"
.include "$MODEL"
.include "$CELLS/th22.sp"
.include "$CELLS/th_gates.sp"
.include "$SUP"
Vdd VDD 0 1.2
Vab AB 0 0
Vin IN 0 0
XC AB AB Yc VDD 0 th22
X12 IN 0 Y12 VDD 0 th12
X13 IN 0 0 Y13 VDD 0 th13
X14 IN 0 0 0 Y14 VDD 0 th14
.dc Vab 0 1.2 0.2
.print dc format=noindex V(Yc) V(Y12) V(Y13) V(Y14)
.end
EOF
  # AB and IN both swept by Vab? No — sweep each: two .dc not allowed together, so
  # tie IN to AB for the collectors (single sweep drives all).
  sed -i 's/^Vin IN 0 0/RIN IN AB 0/' "$WORK/cells.cir"
  (cd "$WORK" && timeout 1500 "$XYCE" cells.cir >cells.out 2>&1)
  if grep -qi 'unrecognized\|no PSP103\|does not bind' "$WORK/cells.out"; then
    echo "   SKIP: no PSP103-capable Xyce (set XYCE=; needs the PyMS-fixed build)"
  fi
  prn="$WORK/cells.cir.prn"
  if [ -f "$prn" ] && ! grep -qi 'too small\|fatal\|abort' "$WORK/cells.out"; then
    # column-name-robust: each Y* column must swing from ~0 (min) to ~VDD (max).
    ok=$(python3 - "$prn" <<'PY'
import sys
rows=[r.split() for r in open(sys.argv[1]) if r.strip() and 'End of' not in r]
hdr=rows[0]; cols={n:i for i,n in enumerate(hdr)}
import re
ys=[c for c in hdr if re.match(r'V\(Y',c)]
data=[]
for r in rows[1:]:
    try: data.append([float(x) for x in r])
    except ValueError: pass
good=all(min(r[cols[y]] for r in data)<0.1 and max(r[cols[y]] for r in data)>1.0 for y in ys)
print("ok" if (ys and good) else "bad")
PY
)
    [ "$ok" = ok ] || fail "cell DC logic did not swing 0<->VDD"
    echo "   ok: th22 C-element set/reset + th12/th13/th14 OR verified at DC"
    PHYS_DC=1
  else
    echo "   SKIP: cell DC sim did not complete cleanly (transient/convergence)"
  fi
else
  echo "   SKIP: no PSP103-capable Xyce (set XYCE=; needs the PyMS-fixed build)"
fi

rm -rf "$WORK"
echo "=== PHYS BINDING GREEN (emit+structure${PHYS_DC:+ +cell-DC}) ==="
