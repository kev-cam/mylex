#!/bin/bash
# Differential test of the translated VX_execute against Icarus, both tiers:
#   gen_tb.py --tier (port map + recorder + replay bench from ports_<tier>.txt, written to OUT)
#   sv2v (DUT + tb_exec) -> iverilog/vvp -> OUT/vectors.txt                 [oracle]
#   nvc -a exec.vhd tb_exec_replay.vhd -> nvc -e/-r tb_exec_replay           [replay: PASS/FAIL]
# usage: ./run_tb.sh [tierA|tierB] [oracle|replay|rerun|all] [outdir]   (default tierA all ./out_<tier>)
# Everything is written under OUT so a Tier B run never touches the Tier A evidence files.
set -u
TIER=${1:-tierA}
STEP=${2:-all}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${3:-$HERE/out_$TIER}
IVL=${IVL:-/usr/local/src/iverilog/_install}
NVC=${NVC:-/usr/local/src/nvc/build}
SV2V=${SV2V:-/home/claude/tools/sv2v/sv2v-Linux/sv2v}
VORTEX=${VORTEX:-/usr/local/src/vortex}
VXINC=${VXINC:-/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/alutest/inc}
R=$VORTEX/hw/rtl
export PATH=$IVL/bin:$NVC/bin:$PATH NVC_LIBPATH=$NVC/lib LD_LIBRARY_PATH=$IVL/lib

DEFS="$(cat $HERE/defs.txt)"
if [ "$TIER" = tierA ]; then
  DEFS="$DEFS -DVX_CFG_EXT_F_DISABLE"; FPU_SRCS=""
else
  DEFS="$DEFS -DASIC"
  FPU_SRCS="$R/fpu/VX_fpu_pkg.sv $R/fpu/VX_fpu_csr_if.sv $R/fpu/VX_fpu_unit.sv $R/fpu/VX_fpu_std.sv $R/fpu/VX_fncp_unit.sv $R/fpu/VX_fp_classifier.sv $R/fpu/VX_fcvt_unit.sv $R/fpu/VX_fp_rounding.sv $R/fpu/VX_fdivsqrt_unit.sv $R/fpu/VX_fma_unit.sv $R/fpu/VX_fma_unit_rtl.sv $R/fpu/VX_fsqrt_unit.sv $R/fpu/VX_fsqrt_unit_rtl.sv $R/fpu/VX_fdiv_unit.sv $R/fpu/VX_fdiv_unit_rtl.sv"
fi
INCS="-I$R -I$R/interfaces -I$R/libs -I$R/core -I$R/fpu -I$VORTEX/hw/dpi -I$VXINC"
IFS_SRCS="$R/interfaces/VX_{lsu_sched,dispatch,commit,sched_csr,branch_ctl,warp_ctl,dcr_csr,execute,result,txbar_bus}_if.sv"
CORE_SRCS="$R/core/VX_{execute,alu_unit,alu_int,alu_muldiv,lsu_unit,lsu_slice,lsu_agu,sfu_unit,csr_unit,csr_data,wctl_unit,lane_gather,lane_dispatch,pe_switch}.sv"

[ -f $OUT/exec.vhd ] || { echo "$OUT/exec.vhd missing: run ./run.sh $TIER $OUT first"; exit 1; }
# the port list the benches are generated from must be the one sv2v resolved for this DUT
diff <(awk '{print $1,$2,$3}' $OUT/ports.txt) <(awk '{print $1,$2,$3}' $HERE/ports_$TIER.txt) > /dev/null \
  || { echo "ports_$TIER.txt differs from $OUT/ports.txt (regenerate: cp $OUT/ports.txt ports_$TIER.txt)"; exit 1; }
python3 $HERE/gen_tb.py --tier $TIER --outdir $OUT || exit 1
cd $OUT

if [ "$STEP" = all ] || [ "$STEP" = oracle ]; then
  echo "== sv2v (tb_exec + DUT)"
  eval $SV2V --top=tb_exec $DEFS $INCS $R/VX_gpu_pkg.sv $IFS_SRCS $R/libs/*.sv $FPU_SRCS $CORE_SRCS $OUT/exec_top.sv tb_exec.sv -w tb.v
  rc=$?; echo "sv2v rc=$rc"; [ $rc -ne 0 ] && exit 1
  echo "== iverilog"
  iverilog -g2012 -s tb_exec -o tb.vvp tb.v 2>&1 | tee iverilog.log | grep -v "warning: Port" | head -30
  rc=${PIPESTATUS[0]}; echo "iverilog rc=$rc"; [ $rc -ne 0 ] && exit 1
  echo "== vvp"
  rm -f vectors.txt
  vvp -n tb.vvp 2>&1 | tee vvp.log | tail -5
  echo "vectors: $(wc -l < vectors.txt) lines, $(wc -c < vectors.txt) bytes"
fi

if [ "$STEP" = all ] || [ "$STEP" = replay ] || [ "$STEP" = rerun ]; then
  if [ "$STEP" = rerun ]; then
    echo "== nvc -a (replay bench only; DUT already in $OUT/work)"
    nvc --std=2040 -a tb_exec_replay.vhd 2>&1 | tee nvc_a_tb.log | grep -v "^$" | tail -20
  else
    echo "== nvc -a (DUT + replay bench)"
    nvc --std=2040 -a exec.vhd tb_exec_replay.vhd 2>&1 | tee nvc_a_tb.log | grep -v "^$" | tail -20
  fi
  rc=${PIPESTATUS[0]}; echo "nvc -a rc=$rc"; [ $rc -ne 0 ] && exit 1
  echo "== nvc -e"
  nvc --std=2040 -e tb_exec_replay 2>&1 | tee nvc_e_tb.log | tail -20
  rc=${PIPESTATUS[0]}; echo "nvc -e rc=$rc"; [ $rc -ne 0 ] && exit 1
  echo "== nvc -r"
  nvc --std=2040 -r tb_exec_replay 2>&1 | tee nvc_r_tb.log | grep -v "^$" | tail -50
  rc=${PIPESTATUS[0]}; echo "nvc -r rc=$rc"
fi
