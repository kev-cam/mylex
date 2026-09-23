#!/bin/bash
# Synthesize ONE Vortex GPU block as async NCL: RTL -> sv2v -> yosys gate netlist
# -> map_ncl.py (dual-rail NCL). Reports whether each step works + the scale.
# Usage: gpu_synth.sh <TOP_MODULE> <workdir>
set -o pipefail
TOP="$1"; WD="${2:-/tmp/gpusyn/$TOP}"; mkdir -p "$WD"; cd "$WD"
V=/home/claude/vortex; R=$V/hw/rtl; B=$V/build/hw
SV2V=/home/claude/tools/bin/sv2v; YS=/usr/local/src/yosys-build/yosys
MAPNCL=/usr/local/src/mylex/nulex/map_ncl.py
FILES=/home/claude/fsmspec/vortex2p/vx_files4.txt
INC="-I$B -I$V/build/sw -I$R -I$V/hw/dpi -I$V/sim/rtlsim -I$R/libs -I$R/interfaces -I$R/core -I$R/mem -I$R/cache -I$R/fpu"

echo "### $TOP: 1. sv2v flatten ###"
$SV2V --top="$TOP" --define=VX_CFG_XLEN=32 --define=VX_CFG_XLEN_32 --define=SYNTHESIS \
  $INC $(cat "$FILES") > "$TOP.v" 2> sv2v.err
SV2V_RC=$?
echo "  sv2v rc=$SV2V_RC  lines=$(wc -l < "$TOP.v" 2>/dev/null)  err_tail=[$(tail -1 sv2v.err)]"
[ "$SV2V_RC" -ne 0 -o ! -s "$TOP.v" ] && { echo "RESULT $TOP: SV2V_FAIL"; exit 1; }

echo "### $TOP: 2. yosys -> gate netlist ###"
cat > synth.ys <<EOF
read_verilog -sv $TOP.v
hierarchy -check -top $TOP
proc; flatten; opt -full
memory_collect; memory_map; opt -full
techmap; opt -full
dfflegalize -cell \$_DFF_P_ x
simplemap; opt_clean
write_json $TOP.json
stat
EOF
$YS -q synth.ys > yosys.log 2>&1
YS_RC=$?
CELLS=$(grep -A40 'Number of cells' yosys.log | grep -E '^\s+\$_' | awk '{s+=$2} END{print s}')
echo "  yosys rc=$YS_RC  cells~$CELLS  err_tail=[$(grep -iE 'error|abort' yosys.log | tail -1)]"
[ "$YS_RC" -ne 0 -o ! -s "$TOP.json" ] && { echo "RESULT $TOP: YOSYS_FAIL"; exit 2; }

echo "### $TOP: 3. map_ncl -> dual-rail NCL ###"
python3 "$MAPNCL" "$TOP.json" "$TOP" "${TOP}_ncl.vhd" > mapncl.log 2>&1
MN_RC=$?
NCLLINES=$(wc -l < "${TOP}_ncl.vhd" 2>/dev/null)
NGATES=$(grep -oiE 'ncl_(and2|or2|xor2|mux2|inv|dff)' "${TOP}_ncl.vhd" 2>/dev/null | sort | uniq -c | tr '\n' ' ')
echo "  map_ncl rc=$MN_RC  ncl_vhd_lines=$NCLLINES  err_tail=[$(tail -1 mapncl.log)]"
echo "  NCL gate census: $NGATES"
[ "$MN_RC" -ne 0 -o ! -s "${TOP}_ncl.vhd" ] && { echo "RESULT $TOP: MAPNCL_FAIL"; exit 3; }
echo "RESULT $TOP: SYNTH_OK cells=$CELLS ncl_lines=$NCLLINES"
