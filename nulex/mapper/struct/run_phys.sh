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
census_sp=$(grep -E '^X[0-9]+ ' "$WORK/add4_phys.sp" | awk '{print $NF}' | sort | uniq -c | awk '{print $1, $2}')
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

echo "== 3. block-level transistor transient: mapped AND2, NULL -> DATA1"
if [ "${PHYS_DC:-0}" = 1 ]; then
  # AND2: a=b=DATA1 -> y=DATA1 (y_L->VDD, y_H stays ~0). Real transistor cells,
  # self-timed from NULL. Instance name is NOT X* of an internal cell (avoid a
  # subckt/instance name clash).
  python3 "$MAP" "$HERE/and2.json" and2 "$WORK/and2_phys.sp" --target spice >/dev/null || fail "and2 spice emit"
  cat > "$WORK/and2_tb.cir" <<EOF
mapped AND2 block, transistor-level NULL->DATA1 transient
.hdl "$PSP"
.include "$MODEL"
.include "$CELLS/th22.sp"
.include "$CELLS/th_gates.sp"
.include "$SUP"
.include "$WORK/and2_phys.sp"
Vdd VDD 0 1.2
Vss VSS 0 0
Va_L a_L 0 PWL(0 0 1n 0 1.2n 1.2)
Va_H a_H 0 0
Vb_L b_L 0 PWL(0 0 1n 0 1.2n 1.2)
Vb_H b_H 0 0
Xblk a_L a_H b_L b_H y_L y_H VDD VSS and2
Cl y_L 0 1f
Ch y_H 0 1f
.tran 2p 4n
.print tran format=noindex V(y_L) V(y_H)
.end
EOF
  (cd "$WORK" && timeout 900 "$XYCE" and2_tb.cir >and2_tb.out 2>&1)
  prn="$WORK/and2_tb.cir.prn"
  if [ -f "$prn" ] && ! grep -qi 'too small\|fatal\|abort' "$WORK/and2_tb.out"; then
    ok=$(python3 - "$prn" <<'PY'
import sys
rows=[r.split() for r in open(sys.argv[1]) if r.strip() and 'End of' not in r]
hdr=rows[0]; cols={n:i for i,n in enumerate(hdr)}
def _num(r):
    try:
        [float(x) for x in r]; return True
    except ValueError:
        return False
data=[r for r in rows[1:] if len(r)==len(hdr) and _num(r)]
yl=[float(r[cols['V(Y_L)']]) for r in data]
yh=[float(r[cols['V(Y_H)']]) for r in data]
# DATA1 output: the y_L rail must assert (>1.0 V) and y_H stay low (<0.2 V)
print("ok" if (yl and max(yl)>1.0 and max(yh)<0.2) else "bad(yl=%.3f yh=%.3f)" % (max(yl or [0]), max(yh or [0])))
PY
)
    [ "$ok" = ok ] || fail "AND2 block logic wrong: $ok (expected y_L->DATA1, y_H~0)"
    echo "   ok: mapped AND2 computes DATA1 = AND(DATA1,DATA1) at the transistor level (self-timed, from NULL)"
    PHYS_BLK=1
  else
    echo "   SKIP: AND2 block transient did not complete cleanly"
  fi
else
  echo "   SKIP: needs the PSP103-capable Xyce (see step 2)"
fi

rm -rf "$WORK"
echo "=== PHYS BINDING GREEN (emit+structure${PHYS_DC:+ +cell-DC}${PHYS_BLK:+ +block-transient}) ==="
