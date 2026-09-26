set W /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work
set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db $W/alu.phys_4.5.odb
set ::env(CLKP) 4.5
source $W/constraints.tcl
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
puts "@@@ PLACEMENT WNSmax [sta::worst_slack -max] TNSmax [sta::total_negative_slack -max] WNSmin [sta::worst_slack -min]"
puts "@@@ VIOLATING PATHS (placement basis)"
report_checks -path_delay max -slack_max 0.0 -endpoint_count 50 -group_count 50 -digits 4 -fields {capacitance slew input_pins nets fanout}
puts "@@@ PIN DUMP"
set fh [open $W/sta45_pins.txt w]
foreach inst [get_cells *] {
  set nm [get_name $inst]
  set ref [get_property $inst ref_name]
  foreach p [get_pins -of_objects $inst] {
    set pn [lindex [split [get_name $p] /] end]
    set dir [get_property $p direction]
    set smax ""; set smin ""; set sr ""; set sf ""
    catch {set smax [get_property $p slack_max]}
    catch {set smin [get_property $p slack_min]}
    catch {set sr [get_property $p slew_max_rise]}
    catch {set sf [get_property $p slew_max_fall]}
    puts $fh "PIN $nm $ref $pn $dir slack_max=$smax slack_min=$smin slew_r=$sr slew_f=$sf act={}"
  }
}
close $fh
puts "@@@ GR BASIS FOR CALIBRATION"
set_routing_layers -signal Metal2-Metal5 -clock Metal3-Metal5
global_route -congestion_iterations 30
estimate_parasitics -global_routing
puts "@@@ GR WNSmax [sta::worst_slack -max] TNSmax [sta::total_negative_slack -max]"
puts "@@@ WORST 10 REG2REG"
report_checks -from [all_registers] -to [all_registers] -path_delay max -group_path_count 10 -digits 4 -fields {capacitance slew input_pins nets fanout} > $W/sta45_routed_reg2reg.log
puts "@@@ WORST 10 OVERALL"
report_checks -path_delay max -group_path_count 10 -digits 4 -fields {capacitance slew input_pins nets fanout} > $W/sta45_routed_overall.log
puts "@@@ DONE"
exit
