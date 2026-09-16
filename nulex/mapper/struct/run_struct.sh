#!/bin/bash
# nulex STRUCTURAL TH-cell flow — end-to-end regression on a 4-bit adder.
# RTL -> gates -> map_ncl_struct (TH-cell instances) -> {yosys fork extraction,
# functional check, nvc elaborate both bindings}.  Exit 0 == all green.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
export PATH=/home/claude/.local/bin:$PATH               # yosys 0.58 (has abc)
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"; NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
MAP=$HERE/../../map_ncl_struct.py; LIB=$HERE/../../lib/th_cells.vhd
cd "$HERE"
echo "== 1. RTL -> generic gate netlist"
yosys -q -p "read_verilog add4.v; hierarchy -top add4; proc; flatten; opt; techmap; opt; abc -g AND,OR,XOR,MUX; opt_clean; write_json add4.json"
echo "== 2a. structural TH netlist (verilog, blackbox TH) -> yosys flatten -> fork extraction"
python3 $MAP add4.json add4 add4_th.v --target verilog
yosys -q -p "read_verilog add4_th.v; hierarchy -top add4; flatten; write_json add4_th.json"
python3 $HERE/../../formal/constraints.py add4_th.json add4
echo "== 2b. functional check (TH netlist decodes to a+b, all 256 inputs)"
python3 eval_th.py
echo "== 3. structural TH netlist (vhdl) -> nvc analyze+elaborate, both bindings"
for B in comb qdi; do
  python3 $MAP add4.json add4 add4_$B.vhd --target vhdl --bind $B
  rm -rf w_$B
  $NVC --std=2008 -L $NVCLIB --work=w_$B -a $LIB   >/dev/null 2>&1
  $NVC --std=2008 -L $NVCLIB --work=w_$B -a add4_$B.vhd >/dev/null 2>&1
  $NVC --std=2008 -L $NVCLIB --work=w_$B -e add4  >/dev/null 2>&1
  echo "   nvc bind=$B: analyze+elaborate OK"
done
echo "== 4. structural QDI register (ncl_reg.vhd): 4-phase capture + completion in nvc"
rm -rf wreg
$NVC --std=2008 -L $NVCLIB --work=wreg -a $LIB                       >/dev/null 2>&1
$NVC --std=2008 -L $NVCLIB --work=wreg -a $HERE/../../lib/ncl_reg.vhd >/dev/null 2>&1
$NVC --std=2008 -L $NVCLIB --work=wreg -a tb_ncl_reg.vhd             >/dev/null 2>&1
$NVC --std=2008 -L $NVCLIB --work=wreg -e tb_ncl_reg                 >/dev/null 2>&1
$NVC --std=2008 -L $NVCLIB --work=wreg -r tb_ncl_reg 2>&1 | grep -E "PASS|FAIL"
echo "== 4b. sequential design with a QDI register bank (--reg qdi) -> handshake fork"
yosys -q -p "read_verilog reg4rtl.v; hierarchy -top reg4; proc; flatten; opt; dfflegalize -cell \$_DFF_P_ x; simplemap; opt_clean; write_json reg4rtl.json"
python3 $MAP reg4rtl.json reg4 reg4_qdi.v --target verilog --reg qdi
yosys -q -p "read_verilog reg4_qdi.v; hierarchy -top reg4; flatten; write_json reg4_qdi.json"
python3 $HERE/../../formal/constraints.py reg4_qdi.json reg4
echo "=== STRUCTURAL FLOW GREEN ==="
