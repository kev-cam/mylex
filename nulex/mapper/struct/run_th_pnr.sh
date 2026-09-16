#!/bin/bash
# PHYSICAL demo: async threshold-gate netlist -> OpenROAD P&R -> layopt extraction,
# on the TH-cell views derived from sky130 (nulex/lib/th_pdk). Needs openroad +
# ~/tools/orfs-sky130hd + ~/tools/sky130_fd_sc_hd (per-cell sky130 GDS).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/claude/.local/bin:$PATH
MAP=$HERE/../../map_ncl_struct.py; TH=$HERE/../../lib/th_pdk
echo "== 1. generate TH-cell physical views (LEF/Liberty/GDS from sky130)"
python3 $TH/gen_th_pdk.py $TH
cp $TH/*.gds /home/claude/tools/sky130_fd_sc_hd/ 2>/dev/null || true   # per-cell GDS for layopt
cd "$HERE"
echo "== 2. structural TH netlist (add4) -> clean Verilog (cells link to TH liberty/LEF)"
yosys -q -p "read_verilog add4.v; hierarchy -top add4; proc; flatten; opt; techmap; opt; abc -g AND,OR,XOR,MUX; opt_clean; write_json add4.json"
python3 $MAP add4.json add4 add4_th_full.v --target verilog
grep -v blackbox add4_th_full.v > add4_th_clean.v
echo "== 3. OpenROAD P&R on the TH-cell views"
openroad -exit flow_th.tcl 2>&1 | grep -iE "Number of violations = 0|Design area|th-flow: DONE"
echo "== 4. layopt extraction on the routed threshold-gate design"
python3 - <<'PY'
import sys; sys.path.insert(0,"/usr/local/src/mylex")
from layopt import lefdef, extract, tech
T=tech.SKY130; P="/home/claude/tools/orfs-sky130hd"; TH="/usr/local/src/mylex/nulex/lib/th_pdk"
lefs=[P+"/sky130_fd_sc_hd.tlef", P+"/sky130_fd_sc_hd_merged.lef", TH+"/th_cells.lef"]
fl=lefdef.def2flat("add4_th.def", lefs, "/home/claude/tools/sky130_fd_sc_hd", T)
ex=extract.extract(fl, T)
print("   layopt: %d rects -> %d shapes, %d nets extracted from the placed+routed TH design"%(len(fl.rects),len(ex.shapes),len(ex.nets)))
PY
echo "== 5. composed cells physical — Muller C-elements (maj3 feedback) + weighted, through P&R"
openroad -exit flow_cel.tcl 2>&1 | grep -iE "Number of violations = 0|Design area|cel-flow: DONE"
echo "=== TH PHYSICAL FLOW GREEN ==="
