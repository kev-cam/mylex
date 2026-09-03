#!/bin/bash
# VX_execute (Tier A: ALU+MULDIV, LSU, SFU; F disabled) through the chain:
#   gen_wrapper.py -> exec_top.sv ; sv2v -> exec.v ; iverilog -tvhdl -> exec.vhd ; nvc -a/-e
# usage: ./run.sh [tierA|tierB] [outdir]      (default tierA, ./out_<tier>)
# Environment (defaults are this machine's): IVL, NVC, SV2V, VORTEX, VXINC.
#   VXINC holds VX_config.vh / VX_types.vh generated for tinygpu, XLEN=32:
#     XLEN=32 python3 ci/gen_config.py --config VX_config.toml --output $VXINC/VX_config.vh --format verilog
#     XLEN=32 python3 ci/gen_config.py --config VX_types.toml  --output $VXINC/VX_types.vh  --format verilog --resolved
set -u
TIER=${1:-tierA}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${2:-$HERE/out_$TIER}
IVL=${IVL:-/usr/local/src/iverilog/_install}
NVC=${NVC:-/usr/local/src/nvc/build}
SV2V=${SV2V:-/home/claude/tools/sv2v/sv2v-Linux/sv2v}
VORTEX=${VORTEX:-/usr/local/src/vortex}
VXINC=${VXINC:-/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/alutest/inc}
R=$VORTEX/hw/rtl
export PATH=$IVL/bin:$NVC/bin:$PATH NVC_LIBPATH=$NVC/lib LD_LIBRARY_PATH=$IVL/lib

DEFS="$(cat $HERE/defs.txt)"
if [ "$TIER" = tierA ]; then
  DEFS="$DEFS -DVX_CFG_EXT_F_DISABLE"
  NEX=3
  FPU_SRCS=""
else
  DEFS="$DEFS -DASIC"       # VX_CFG_FPU_TYPE -> STD (soft FPU)
  NEX=4
  FPU_SRCS="$R/fpu/VX_fpu_pkg.sv $R/fpu/VX_fpu_csr_if.sv $R/fpu/VX_fpu_unit.sv $R/fpu/VX_fpu_std.sv $R/fpu/VX_fncp_unit.sv $R/fpu/VX_fp_classifier.sv $R/fpu/VX_fcvt_unit.sv $R/fpu/VX_fp_rounding.sv $R/fpu/VX_fdivsqrt_unit.sv $R/fpu/VX_fma_unit.sv $R/fpu/VX_fma_unit_rtl.sv $R/fpu/VX_fsqrt_unit.sv $R/fpu/VX_fsqrt_unit_rtl.sv $R/fpu/VX_fdiv_unit.sv $R/fpu/VX_fdiv_unit_rtl.sv"
fi
INCS="-I$R -I$R/interfaces -I$R/libs -I$R/core -I$R/fpu -I$VORTEX/hw/dpi -I$VXINC"
IFS_SRCS="$R/interfaces/VX_{lsu_sched,dispatch,commit,sched_csr,branch_ctl,warp_ctl,dcr_csr,execute,result,txbar_bus}_if.sv"
CORE_SRCS="$R/core/VX_{execute,alu_unit,alu_int,alu_muldiv,lsu_unit,lsu_slice,lsu_agu,sfu_unit,csr_unit,csr_data,wctl_unit,lane_gather,lane_dispatch,pe_switch}.sv"

mkdir -p $OUT
python3 $HERE/gen_wrapper.py --num-ex-units $NEX -o $OUT/exec_top.sv || exit 1

echo "== sv2v"
eval $SV2V --top=exec_top $DEFS $INCS $R/VX_gpu_pkg.sv $IFS_SRCS $R/libs/*.sv $FPU_SRCS $CORE_SRCS $OUT/exec_top.sv -w $OUT/exec.v
rc=$?; echo "sv2v rc=$rc"; [ $rc -ne 0 ] && exit 1
python3 $HERE/mk_ports.py $OUT/exec.v > $OUT/ports.txt || exit 1

echo "== iverilog -tnull"
iverilog -g2012 -tnull -s exec_top $OUT/exec.v; echo "tnull rc=$?"
echo "== iverilog vvp compile"
iverilog -g2012 -s exec_top -o $OUT/exec.vvp $OUT/exec.v; echo "vvp-compile rc=$?"

echo "== iverilog -tvhdl"
iverilog -g2012 -tvhdl -psv2vhdl=1 -s exec_top -o $OUT/exec.vhd $OUT/exec.v 2>&1 | tee $OUT/tvhdl.log | tail -30
rc=${PIPESTATUS[0]}; echo "tvhdl rc=$rc"; [ $rc -ne 0 ] && exit 1

echo "== nvc -a"
cd $OUT && nvc --std=2040 -a exec.vhd 2>&1 | tee $OUT/nvc_a.log | grep -c 'Error' ; rc=${PIPESTATUS[0]}; echo "nvc -a rc=$rc"; [ $rc -ne 0 ] && { grep -A6 -m5 '\*\* Error' $OUT/nvc_a.log; exit 1; }
echo "== nvc -e"
nvc --std=2040 -e exec_top 2>&1 | tee $OUT/nvc_e.log | tail -20; rc=${PIPESTATUS[0]}; echo "nvc -e rc=$rc"; [ $rc -ne 0 ] && exit 1
echo "== nvc -r --stop-time=100ns (sanity: no runtime faults with undriven inputs)"
nvc --std=2040 -r --stop-time=100ns exec_top > $OUT/nvc_r100.log 2>&1; echo "nvc -r rc=$?"
