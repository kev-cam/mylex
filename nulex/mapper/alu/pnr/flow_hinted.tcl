# alu_top re-place+route with fork-driven placement hints: relocate each wide
# fork's driver buffer toward its receivers' centroid (fork_targets.tcl), then
# legalize, CTS, route. A/B against alu_top.def (the un-hinted route from the
# same alu_placed.odb). Mirrors flow_alu.tcl's back half.
set P /home/claude/tools/orfs-sky130hd
set D [file dirname [file normalize [info script]]]
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db $D/alu_placed.odb
read_sdc $D/constraint.sdc
source $P/setRC.tcl
source $D/fork_targets.tcl

set block [ord::get_db_block]
set rowh 2720
set moved 0
foreach t $FORK_TARGETS {
    lassign $t nm tx ty
    set net [$block findNet $nm]
    if {$net eq "NULL" || $net eq ""} continue
    set drv ""
    foreach it [$net getITerms] { if {[$it getIoType] eq "OUTPUT"} { set drv $it } }
    if {$drv eq ""} continue
    set inst [$drv getInst]
    set m [[$inst getMaster] getName]
    if {![string match *__buf_* $m] && ![string match *__inv_* $m] && ![string match *__clkinv_* $m]} continue
    set ry [expr {int(round(double($ty)/$rowh))*$rowh}]      ;# snap to a row
    $inst setLocation $tx $ry
    $inst setPlacementStatus PLACED                          ;# PLACED (not FIRM) so DPL can legalize overlaps
    incr moved
}
puts "fork-hint: relocated $moved wide-fork drivers toward receiver centroids"

detailed_placement                                           ;# legalize the moves
optimize_mirroring

clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_16 \
    -buf_list {sky130_fd_sc_hd__clkbuf_16 sky130_fd_sc_hd__clkbuf_8 sky130_fd_sc_hd__clkbuf_4} \
    -sink_clustering_enable
set_propagated_clock [all_clocks]
repair_clock_nets
detailed_placement
estimate_parasitics -placement
repair_timing
detailed_placement
puts "alu-hinted: CTS done"

set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_iterations 30 -verbose
detailed_route -output_drc $D/route_drc_hinted.rpt -verbose 1
filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
check_placement -verbose

estimate_parasitics -global_routing
report_wns
report_tns
report_design_area
write_def $D/alu_top_hinted.def
write_db $D/alu_top_hinted.odb
puts "alu-hinted: DONE -> $D/alu_top_hinted.def"
exit
