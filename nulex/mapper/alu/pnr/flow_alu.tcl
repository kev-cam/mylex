# alu_top: sky130hd place-and-route with OpenROAD (standalone Tcl, no ORFS make).
# Modeled on probes/layopt/gcd/flow.tcl. Produces a detailed-routed DEF that
# layopt's lefdef.def2flat consumes for isochronic-fork balancing.
set P /home/claude/tools/orfs-sky130hd
set D [file dirname [file normalize [info script]]]
set UTIL [expr {[info exists ::env(UTIL)] ? $::env(UTIL) : 35}]

read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog $D/alu_top.sky130.v
link_design alu_top
read_sdc $D/constraint.sdc
source $P/setRC.tcl
set_dont_use {sky130_fd_sc_hd__probe_p_8 sky130_fd_sc_hd__probec_p_8 sky130_fd_sc_hd__lpflow_* sky130_fd_sc_hd__clkinvlp_*}

# ---- floorplan ----
initialize_floorplan -utilization $UTIL -aspect_ratio 1 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
set ::env(TAP_CELL_NAME) sky130_fd_sc_hd__tapvpwrvgnd_1
source $P/tapcell.tcl
source $P/pdn.tcl
pdngen
puts "alu: floorplan + PDN done"

# ---- placement ----
global_placement -skip_io -density 0.70 -pad_left 2 -pad_right 2
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.70 -pad_left 2 -pad_right 2
estimate_parasitics -placement
repair_design
detailed_placement
optimize_mirroring
write_db $D/alu_placed.odb
puts "alu: placement done"

# ---- clock tree ----
clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_16 \
    -buf_list {sky130_fd_sc_hd__clkbuf_16 sky130_fd_sc_hd__clkbuf_8 sky130_fd_sc_hd__clkbuf_4} \
    -sink_clustering_enable
set_propagated_clock [all_clocks]
repair_clock_nets
detailed_placement
estimate_parasitics -placement
repair_timing
detailed_placement
puts "alu: CTS done"

# ---- routing ----
set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_iterations 30 -verbose
detailed_route -output_drc $D/route_drc.rpt -verbose 1
filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
check_placement -verbose
puts "alu: routing done"

# ---- results ----
estimate_parasitics -global_routing
report_wns
report_tns
report_design_area
write_def $D/alu_top.def
write_verilog -include_pwr_gnd $D/alu_top.pnr.v
write_db $D/alu_top.odb
puts "alu: DONE -> $D/alu_top.def"
exit
