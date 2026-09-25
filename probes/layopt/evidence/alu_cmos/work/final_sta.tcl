set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
set CLKP 4.75
source constraints.tcl
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
puts "@@@ WORST OVERALL"
report_checks -path_delay max -group_path_count 1 -digits 4 
puts "@@@ REG-TO-REG ONLY"
report_checks -from [all_registers] -to [all_registers] -path_delay max -group_path_count 3 -digits 4 
puts "@@@ INPUT-TO-REG ONLY"
report_checks -from [all_inputs] -to [all_registers] -path_delay max -group_path_count 1 -digits 4 
puts "@@@ REG-TO-OUTPUT ONLY"
report_checks -from [all_registers] -to [all_outputs] -path_delay max -group_path_count 1 -digits 4 
puts "@@@ DRV"
report_check_types -max_fanout -max_capacitance -max_slew -violators
