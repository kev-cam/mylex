#!/bin/bash
# nulex: VX_execute (Tier A: ALU+MULDIV, LSU, SFU; F disabled) -> dual-rail NCL.
#   VX_execute.sv --sv2v--> exec.v --yosys--> gate netlist --map_ncl.py-->
#   exec_top_ncl.vhd (dual-rail comb + sync-emulation regs).
# Verification here is SELF-CONTAINED: map_plain.py emits a std_logic reference
# from the same gate netlist, and gen_ncl_diff.py drives both with identical
# random stimulus in one NVC sim, asserting every output matches every cycle.
# (The committed vvp oracle vectors don't align: this box's Vortex differs from
#  the probes' by 2 bits in lsu req_data, and sv2v/iverilog here can't resolve
#  the cta_lane_t type() the probes' toolchain did. The ALU flow (run_alu.sh)
#  already proved the mapper against the independent vvp oracle.)
set -e
VORTEX="${VORTEX:-/home/claude/vortex}"
PROBES="${PROBES:-/usr/local/src/mylex/probes/exectest}"
SV2V="${SV2V:-/home/claude/tools/bin/sv2v}"
YS="${YS:-/usr/local/src/yosys-build/yosys}"
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"
NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
NULEX=/usr/local/src/mylex/nulex
cd "$(dirname "$0")"; mkdir -p work
R="$VORTEX/hw/rtl"
DEFS="$(cat "$PROBES/defs.txt") -DVX_CFG_EXT_F_DISABLE"
INCS="-I$R -I$R/interfaces -I$R/libs -I$R/core -I$R/fpu -I$VORTEX/hw/dpi -I$VORTEX/inc"
IFS_SRCS="$R/interfaces/VX_lsu_sched_if.sv $R/interfaces/VX_dispatch_if.sv $R/interfaces/VX_commit_if.sv $R/interfaces/VX_sched_csr_if.sv $R/interfaces/VX_branch_ctl_if.sv $R/interfaces/VX_warp_ctl_if.sv $R/interfaces/VX_dcr_csr_if.sv $R/interfaces/VX_execute_if.sv $R/interfaces/VX_result_if.sv $R/interfaces/VX_txbar_bus_if.sv"
CORE_SRCS="$R/core/VX_execute.sv $R/core/VX_alu_unit.sv $R/core/VX_alu_int.sv $R/core/VX_alu_muldiv.sv $R/core/VX_lsu_unit.sv $R/core/VX_lsu_slice.sv $R/core/VX_lsu_agu.sv $R/core/VX_sfu_unit.sv $R/core/VX_csr_unit.sv $R/core/VX_csr_data.sv $R/core/VX_wctl_unit.sv $R/core/VX_lane_gather.sv $R/core/VX_lane_dispatch.sv $R/core/VX_pe_switch.sv"

echo "=== 1. config headers ==="
( cd "$VORTEX" && mkdir -p inc \
  && XLEN=32 python3 ci/gen_config.py --config VX_config.toml --output inc/VX_config.vh --format verilog \
  && XLEN=32 python3 ci/gen_config.py --config VX_types.toml  --output inc/VX_types.vh  --format verilog --resolved )
echo "=== 2. sv2v flatten VX_execute -> work/exec.v ==="
eval $SV2V --top=exec_top $DEFS $INCS $R/VX_gpu_pkg.sv $IFS_SRCS '$R/libs/*.sv' $CORE_SRCS "$PROBES/exec_top.sv" -w work/exec.v
# older yosys/iverilog lack the SV type() operator in $bits; resolve cta_lane_t (6 bits)
sed -i 's/\$bits(type(cta_lane_t))/6/g' work/exec.v
echo "=== 3. yosys -> gate netlist (memory lowered, reset folded to $_DFF_P_) ==="
$YS -q synth_exec.ys
python3 -c 'import json;m=json.load(open("work/exec.json"))["modules"]["exec_top"];\
import collections;print("cells:",dict(collections.Counter(c["type"] for c in m["cells"].values())))'
echo "=== 4. derive manifest from JSON + map to dual-rail NCL + plain reference ==="
python3 -c '
import json
m=json.load(open("work/exec.json"))["modules"]["exec_top"]
open("work/ports.txt","w").write("".join("%-7s %d %s\n"%(v["direction"],len(v["bits"]),n) for n,v in m["ports"].items()))'
python3 $NULEX/map_ncl.py   work/exec.json exec_top work/exec_top_ncl.vhd
python3 $NULEX/map_plain.py work/exec.json exec_top work/exec_top_plain.vhd
echo "=== 5. self-contained equivalence: NCL vs plain, random stimulus ==="
python3 $NULEX/gen_ncl_diff.py work/ports.txt exec_top work/tb_exec_top_diff.vhd 200
A=(--std=2008 -M 1g -L "$NVCLIB" --work=work/dwork)
rm -rf work/dwork
$NVC "${A[@]}" -a ../../lib/ncl_gates.vhd
$NVC "${A[@]}" -a work/exec_top_ncl.vhd
$NVC "${A[@]}" -a work/exec_top_plain.vhd
$NVC "${A[@]}" -a work/tb_exec_top_diff.vhd
$NVC "${A[@]}" -e tb_exec_top_diff
$NVC "${A[@]}" -r tb_exec_top_diff
echo "=== EXEC FLOW DONE ==="
