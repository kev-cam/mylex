#!/bin/bash
# nulex netlist-mapper end-to-end proof:
#   small.v --yosys(synth.ys)--> work/small.json --map_ncl.py--> work/small_ncl.vhd
#   then NVC-simulate the mapped dual-rail NCL netlist vs the sync golden.
# Exit 0 == the mapped NCL netlist matches the synchronous RTL over the sweep.
set -e
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"
NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
YS="${YS:-/usr/local/src/yosys-build/yosys}"
cd "$(dirname "$0")"
echo "=== 1. synth small.v -> gate netlist JSON ==="
$YS -q synth.ys
echo "=== 2. map JSON -> dual-rail NCL VHDL ==="
python3 ../map_ncl.py work/small.json small work/small_ncl.vhd
echo "=== 3. NVC: gate lib + mapped netlist + tb ==="
A=( --std=2008 -L "$NVCLIB" --work=mwork )
rm -rf mwork
$NVC "${A[@]}" -a ../lib/ncl_gates.vhd
$NVC "${A[@]}" -a work/small_ncl.vhd
$NVC "${A[@]}" -a tb_small_ncl.vhd
$NVC "${A[@]}" -e tb_small_ncl
$NVC "${A[@]}" -r tb_small_ncl
echo "=== MAPPER PROOF DONE ==="
