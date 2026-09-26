set_thread_count 12
set W /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work
set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db $W/alu.phys_4.75.odb
set ::env(CLKP) 4.75
source $W/constraints.tcl
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
set_routing_layers -signal Metal2-Metal5 -clock Metal3-Metal5
global_route -congestion_iterations 30
estimate_parasitics -global_routing
puts "@@@ POST-GR WNS [sta::worst_slack -max] TNS [sta::total_negative_slack -max]"
detailed_route -output_drc route475mt_drc.rpt -verbose 1
puts "@@@ POST-DR DONE"
estimate_parasitics -global_routing
puts "@@@ POST-DR WNS [sta::worst_slack -max] TNS [sta::total_negative_slack -max]"
write_def alu_4.75_routed_mt.def
write_db alu_4.75_routed_mt.odb
puts "@@@ WORST 10 REG2REG"
report_checks -from [all_registers] -to [all_registers] -path_delay max -group_path_count 10 -digits 4 -fields {capacitance slew input_pins nets fanout}
puts "@@@ WORST 10 OVERALL"
report_checks -path_delay max -group_path_count 10 -digits 4 -fields {capacitance slew input_pins nets fanout}
puts "@@@ ALL DONE"
exit
