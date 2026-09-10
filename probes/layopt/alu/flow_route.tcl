# layopt: routing half of the gcd flow, from the pre-route database.  Set the env
# var HINTS to a Tcl file of placer hints (layopt/placer.py) to source before
# routing, and TAG for the output names.
set P /home/claude/tools/orfs-sky130hd
set D /home/claude/src/alu-flow/hints
set tag [expr {[info exists ::env(TAG)] ? $::env(TAG) : "base"}]
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db $D/alu_placed.odb
read_sdc /home/claude/src/alu-flow/constraint.sdc
source $P/setRC.tcl
set_propagated_clock [all_clocks]
if {[info exists ::env(HINTS)]} {
    puts "layopt: sourcing placer hints $::env(HINTS)"
    source $::env(HINTS)
    check_placement -verbose
}
write_def $D/alu_${tag}_placed.def
estimate_parasitics -placement
puts "layopt: pre-route WNS [sta::worst_slack -max] TNS [sta::total_negative_slack -max]"
set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_iterations 30 -verbose
detailed_route -output_drc $D/route_drc_$tag.rpt -verbose 1
filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
check_placement -verbose
estimate_parasitics -global_routing
report_wns
report_tns
report_design_area
write_def $D/alu_$tag.def
exit
