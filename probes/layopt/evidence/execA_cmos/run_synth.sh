#!/bin/bash
# VX_execute Tier A (nulex no-FPU revision, /home/claude/vortex) -> IHP SG13G2
# stdcells. SAME recipe as ../alu_cmos/run_synth.sh (the E_tree anchor).
set -e
RTL=/usr/local/src/mylex/nulex/mapper/exec/work/exec.v
LIB=/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
D=/usr/local/src/mylex/probes/layopt/evidence/execA_cmos
cd $D/work
yosys -p "read_verilog $RTL; hierarchy -top exec_top; synth -top exec_top -flatten; \
  dfflibmap -liberty $LIB; abc -liberty $LIB; opt_clean; \
  tee -o cmos_stat.txt stat -liberty $LIB; write_verilog -noattr exec.cmos.v" 2>&1 | tee synth.log | tail -30
