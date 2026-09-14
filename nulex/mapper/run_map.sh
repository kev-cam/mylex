#!/bin/bash
# nulex netlist-mapper end-to-end proofs (RTL -> yosys gate netlist ->
# map_ncl.py -> dual-rail NCL VHDL -> NVC vs sync golden). Exit 0 == all match.
#   small : combinational  (y = sel ? a+b : a^b)                512 cases
#   acc   : sequential     (r <= rst?0:r+din; sync-emu register) 16 cycles
set -e
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"
NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
YS="${YS:-/usr/local/src/yosys-build/yosys}"
cd "$(dirname "$0")"
A=( --std=2008 -L "$NVCLIB" )

run_one () {  # <ys-script> <json> <top> <tb-top> <tb-file>
  local ys=$1 json=$2 top=$3 tbtop=$4 tbf=$5
  echo "=== [$top] synth -> map -> simulate ==="
  $YS -q "$ys"
  python3 ../map_ncl.py "work/$json" "$top" "work/${top}_ncl.vhd"
  rm -rf "mwork_$top"
  $NVC "${A[@]}" --work="mwork_$top" -a ../lib/ncl_gates.vhd
  $NVC "${A[@]}" --work="mwork_$top" -a "work/${top}_ncl.vhd"
  $NVC "${A[@]}" --work="mwork_$top" -a "$tbf"
  $NVC "${A[@]}" --work="mwork_$top" -e "$tbtop"
  $NVC "${A[@]}" --work="mwork_$top" -r "$tbtop"
}

run_one synth.ys     small.json small tb_small_ncl tb_small_ncl.vhd
run_one synth_seq.ys acc.json   acc   tb_acc_ncl   tb_acc_ncl.vhd
echo "=== ALL MAPPER PROOFS GREEN ==="
