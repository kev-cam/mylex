#!/bin/bash
# nulex: VX_execute Tier B (+ soft FPU, NUM_EX_UNITS=4, -DASIC) -> dual-rail NCL.
#   gen_wrapper.py --num-ex-units 4 -> exec_top_tierB.sv ; sv2v -> exec_tierB.v ;
#   yosys (memory lowered, reset folded) -> gate netlist ; map_ncl.py -> NCL.
# Verified self-contained (NCL vs plain, random stimulus) like Tier A; the vvp
# oracle is blocked here (Vortex drift + cta_lane_t type()). The soft FPU uses
# the SAME gate primitives as Tier A -- this proves the mapper at ~3x scale.
# ~126k cells; NVC needs a large -M and this is a long run (see NVCMEM below).
set -e
VORTEX="${VORTEX:-/home/claude/vortex}"
PROBES="${PROBES:-/usr/local/src/mylex/probes/exectest}"
SV2V="${SV2V:-/home/claude/tools/bin/sv2v}"
YS="${YS:-/usr/local/src/yosys-build/yosys}"
NVC="${NVC:-/usr/local/src/nvc-build/bin/nvc}"
NVCLIB="${NVCLIB:-/usr/local/src/nvc-build/lib}"
NVCMEM="${NVCMEM:-4g}"   # -M per-unit analyze limit (136k-line netlist)
NVCHEAP="${NVCHEAP:-8g}" # -H elaboration/sim heap (~125k instances; needs ~<9G RAM)
NULEX=/usr/local/src/mylex/nulex
cd "$(dirname "$0")"; mkdir -p work
R="$VORTEX/hw/rtl"
DEFS="$(cat "$PROBES/defs.txt") -DASIC"     # -DASIC -> soft FPU (VX_CFG_FPU_TYPE=STD)
INCS="-I$R -I$R/interfaces -I$R/libs -I$R/core -I$R/fpu -I$VORTEX/hw/dpi -I$VORTEX/inc"
IFS_SRCS="$R/interfaces/VX_lsu_sched_if.sv $R/interfaces/VX_dispatch_if.sv $R/interfaces/VX_commit_if.sv $R/interfaces/VX_sched_csr_if.sv $R/interfaces/VX_branch_ctl_if.sv $R/interfaces/VX_warp_ctl_if.sv $R/interfaces/VX_dcr_csr_if.sv $R/interfaces/VX_execute_if.sv $R/interfaces/VX_result_if.sv $R/interfaces/VX_txbar_bus_if.sv"
FPU_SRCS="$R/fpu/VX_fpu_pkg.sv $R/fpu/VX_fpu_csr_if.sv $R/fpu/VX_fpu_unit.sv $R/fpu/VX_fpu_std.sv $R/fpu/VX_fncp_unit.sv $R/fpu/VX_fp_classifier.sv $R/fpu/VX_fcvt_unit.sv $R/fpu/VX_fp_rounding.sv $R/fpu/VX_fdivsqrt_unit.sv $R/fpu/VX_fma_unit.sv $R/fpu/VX_fma_unit_rtl.sv $R/fpu/VX_fsqrt_unit.sv $R/fpu/VX_fsqrt_unit_rtl.sv $R/fpu/VX_fdiv_unit.sv $R/fpu/VX_fdiv_unit_rtl.sv"
CORE_SRCS="$R/core/VX_execute.sv $R/core/VX_alu_unit.sv $R/core/VX_alu_int.sv $R/core/VX_alu_muldiv.sv $R/core/VX_lsu_unit.sv $R/core/VX_lsu_slice.sv $R/core/VX_lsu_agu.sv $R/core/VX_sfu_unit.sv $R/core/VX_csr_unit.sv $R/core/VX_csr_data.sv $R/core/VX_wctl_unit.sv $R/core/VX_lane_gather.sv $R/core/VX_lane_dispatch.sv $R/core/VX_pe_switch.sv"

echo "=== 1. config headers ==="
( cd "$VORTEX" && mkdir -p inc \
  && XLEN=32 python3 ci/gen_config.py --config VX_config.toml --output inc/VX_config.vh --format verilog \
  && XLEN=32 python3 ci/gen_config.py --config VX_types.toml  --output inc/VX_types.vh  --format verilog --resolved )
echo "=== 2. gen_wrapper (NUM_EX_UNITS=4) + sv2v -> work/exec_tierB.v ==="
python3 "$PROBES/gen_wrapper.py" --num-ex-units 4 -o work/exec_top_tierB.sv
eval $SV2V --top=exec_top $DEFS $INCS $R/VX_gpu_pkg.sv $IFS_SRCS '$R/libs/*.sv' $FPU_SRCS $CORE_SRCS work/exec_top_tierB.sv -w work/exec_tierB.v
sed -i 's/\$bits(type(cta_lane_t))/6/g' work/exec_tierB.v
echo "=== 3. yosys -> gate netlist (slow: the soft FPU) ==="
$YS -q synth_exec_tierB.ys
python3 -c 'import json,collections;m=json.load(open("work/exec_tierB.json"))["modules"]["exec_top"];\
print("cells:",dict(collections.Counter(c["type"] for c in m["cells"].values())))'
echo "=== 4. map to dual-rail NCL + plain reference ==="
python3 -c 'import json;m=json.load(open("work/exec_tierB.json"))["modules"]["exec_top"];\
open("work/ports_tierB.txt","w").write("".join("%-7s %d %s\n"%(v["direction"],len(v["bits"]),n) for n,v in m["ports"].items()))'
python3 $NULEX/map_ncl.py   work/exec_tierB.json exec_top work/exec_top_ncl_tierB.vhd
python3 $NULEX/map_plain.py work/exec_tierB.json exec_top work/exec_top_plain_tierB.vhd
echo "=== 5. self-contained equivalence: NCL vs plain (NVC -M $NVCMEM, long) ==="
python3 $NULEX/gen_ncl_diff.py work/ports_tierB.txt exec_top work/tb_exec_tierB_diff.vhd 200
A=(--std=2008 -M "$NVCMEM" -H "$NVCHEAP" -L "$NVCLIB" --work=work/dworkB)
rm -rf work/dworkB
$NVC "${A[@]}" -a ../../lib/ncl_gates.vhd
$NVC "${A[@]}" -a work/exec_top_ncl_tierB.vhd
$NVC "${A[@]}" -a work/exec_top_plain_tierB.vhd
$NVC "${A[@]}" -a work/tb_exec_tierB_diff.vhd
$NVC "${A[@]}" -e tb_exec_top_diff
$NVC "${A[@]}" -r tb_exec_top_diff
echo "=== EXEC TIER B FLOW DONE ==="
