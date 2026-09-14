#!/bin/bash
# nulex: VX_alu_int (real Vortex integer ALU) -> dual-rail NCL, verified vs the
# committed vvp-oracle vectors (the 3-oracle differential, probes/alutest).
#   VX_alu_int.sv --sv2v--> alu.v --yosys--> gate netlist --map_ncl.py-->
#   alu_top_ncl.vhd (QDI dual-rail comb + sync-emulation regs) --NVC--> replay
# Exit 0 == the mapped async ALU matches the synchronous oracle (42 cyc).
#
# External inputs (not in this repo): the Vortex RTL ($VORTEX) and the tools
# (sv2v, yosys, nvc). The oracle vectors + flat-port wrapper come from
# probes/alutest ($PROBES).
set -e
VORTEX="${VORTEX:-/home/claude/vortex}"
PROBES="${PROBES:-/usr/local/src/mylex/probes/alutest}"
SV2V="${SV2V:-/home/claude/tools/bin/sv2v}"
YS="${YS:-/usr/local/src/yosys-build/yosys}"
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"
NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
cd "$(dirname "$0")"
mkdir -p work

echo "=== 1. config headers (gen_config) ==="
( cd "$VORTEX" && mkdir -p inc \
  && XLEN=32 python3 ci/gen_config.py --config VX_config.toml --output inc/VX_config.vh --format verilog \
  && XLEN=32 python3 ci/gen_config.py --config VX_types.toml  --output inc/VX_types.vh  --format verilog --resolved )

echo "=== 2. sv2v flatten VX_alu_int -> work/alu.v ==="
DEFS=$(cat "$PROBES/defs.txt"); R="$VORTEX/hw/rtl"
$SV2V --top=alu_top $DEFS -I"$R" -I"$R/interfaces" -I"$R/libs" -I"$R/core" -I"$R/fpu" -I"$VORTEX/hw/dpi" -I"$VORTEX/inc" \
  "$R/VX_gpu_pkg.sv" "$R/interfaces/VX_execute_if.sv" "$R/interfaces/VX_result_if.sv" "$R/interfaces/VX_branch_ctl_if.sv" \
  "$R"/libs/*.sv "$R/core/VX_alu_int.sv" "$PROBES/alu_top.sv" -w work/alu.v

echo "=== 3. yosys -> gate netlist JSON ==="
$YS -q synth_alu.ys

echo "=== 4. map_ncl.py -> dual-rail NCL netlist ==="
python3 ../../map_ncl.py work/alu.json alu_top work/alu_top_ncl.vhd

echo "=== 5. NVC replay vs vvp oracle ==="
cp "$PROBES/vectors.txt" ./vectors.txt
rm -rf mwork
A=( --std=2008 -L "$NVCLIB" --work=mwork )
$NVC "${A[@]}" -a ../../lib/ncl_gates.vhd
$NVC "${A[@]}" -a work/alu_top_ncl.vhd
$NVC "${A[@]}" -a tb_alu_ncl_replay.vhd
$NVC "${A[@]}" -e tb_alu_ncl_replay
$NVC "${A[@]}" -r tb_alu_ncl_replay
echo "=== ALU MAPPER FLOW DONE ==="
