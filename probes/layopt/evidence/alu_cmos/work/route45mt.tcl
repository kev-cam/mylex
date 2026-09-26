set_thread_count 12
set W /usr/local/src/mylex/probes/layopt/evidence/alu_cmos/work
set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db $W/alu.phys_4.5.odb
set ::env(CLKP) 4.5
source $W/constraints.tcl
set_propagated_clock [all_clocks]
# one_/zero_ are the constant RESET_B tie nets (no driver cell in this ODB;
# the 4.75 anchor used tie cells).  DRT-0305 refuses POWER/GROUND-typed signal
# nets; they are static, so route them as ordinary signals.
set blk [ord::get_db_block]
foreach nm {one_ zero_} {
  set n [$blk findNet $nm]
  if {$n ne "NULL"} { $n setSigType "SIGNAL"; puts "@@@ retyped $nm to SIGNAL" }
}
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
set_routing_layers -signal Metal2-Metal5 -clock Metal3-Metal5
global_route -congestion_iterations 30
estimate_parasitics -global_routing
puts "@@@ POST-GR WNS [sta::worst_slack -max] TNS [sta::total_negative_slack -max]"
detailed_route -output_drc route45mt_drc.rpt -verbose 1
puts "@@@ POST-DR DONE"
estimate_parasitics -global_routing
puts "@@@ POST-DR WNS [sta::worst_slack -max] TNS [sta::total_negative_slack -max]"
write_def alu_4.5_routed_mt.def
write_db alu_4.5_routed_mt.odb
puts "@@@ ALL DONE"
exit
