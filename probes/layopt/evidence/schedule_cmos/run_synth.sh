#!/bin/bash
# schedule island (rtlmeter-tree Vortex 'mini', flat-netlist island extraction) ->
# IHP SG13G2 stdcells. SAME recipe as ../alu_cmos/run_synth.sh (the E_tree anchor).
# schedule_isl.json was produced by extract_island.py (copy in this dir) from
# vortex_flat.json (regenerable: /home/claude/vortex_static_char/reproduce.sh);
# island attribution is IDENTICAL to flat_islands.py / consolidated_vector.txt.
# $mem cells are externalized (SRAM macros, not flop sinks).
set -e
LIB=/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
D=/usr/local/src/mylex/probes/layopt/evidence/schedule_cmos
cd $D/work
yosys -p "read_json $D/schedule_isl.json; hierarchy -top schedule_isl; synth -top schedule_isl -flatten; \
  dfflibmap -liberty $LIB; abc -liberty $LIB; opt_clean; \
  tee -o cmos_stat.txt stat -liberty $LIB; write_verilog -noattr schedule.cmos.v" 2>&1 | tee synth.log | tail -30
