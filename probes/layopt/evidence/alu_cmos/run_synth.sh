#!/bin/bash
# alu_top -> IHP SG13G2 stdcells, same flow as qal/synth/run_regular.sh
set -e
RTL=/usr/local/src/mylex/nulex/mapper/alu/work/alu.v
LIB=/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
D=/usr/local/src/mylex/probes/layopt/evidence/alu_cmos
cd $D/work
yosys -p "read_verilog $RTL; hierarchy -top alu_top; synth -top alu_top -flatten; \
  dfflibmap -liberty $LIB; abc -liberty $LIB; opt_clean; \
  tee -o cmos_stat.txt stat -liberty $LIB; write_verilog -noattr alu.cmos.v" 2>&1 | tail -80
