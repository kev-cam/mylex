set W /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work
set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db $W/alu.phys_4.5.odb
set ::env(CLKP) 4.5
source $W/constraints.tcl
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
puts "@@@ BEFORE WNSmax [sta::worst_slack -max] TNSmax [sta::total_negative_slack -max] WNSmin [sta::worst_slack -min]"
puts "@@@ AFTER WNSmax [sta::worst_slack -max] TNSmax [sta::total_negative_slack -max] WNSmin [sta::worst_slack -min]"
puts "@@@ PATHS"
report_checks -path_delay max -slack_max 0.0 -endpoint_count 20 -group_count 20 -digits 4
puts "@@@ DONE"
exit
