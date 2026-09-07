# layopt: sky130hd place-and-route of gcd with OpenROAD (standalone Tcl, no ORFS make)
set P /home/claude/tools/orfs-sky130hd
set D /home/claude/src/gcd-flow
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog $D/gcd_synth.v
link_design gcd
read_sdc $P/constraint.sdc
source $P/setRC.tcl
set_dont_use {sky130_fd_sc_hd__probe_p_8 sky130_fd_sc_hd__probec_p_8 sky130_fd_sc_hd__lpflow_* sky130_fd_sc_hd__clkinvlp_*}

# floorplan
initialize_floorplan -utilization 38 -aspect_ratio 1 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
set ::env(TAP_CELL_NAME) sky130_fd_sc_hd__tapvpwrvgnd_1
source $P/tapcell.tcl
source $P/pdn.tcl
pdngen

# placement: io-less placement first, then pins, then the real placement
global_placement -skip_io -density 0.60 -pad_left 4 -pad_right 4
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.60 -pad_left 4 -pad_right 4
estimate_parasitics -placement
repair_design
detailed_placement
optimize_mirroring

# clock tree
clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_16 -buf_list {sky130_fd_sc_hd__clkbuf_16 sky130_fd_sc_hd__clkbuf_8 sky130_fd_sc_hd__clkbuf_4} -sink_clustering_enable
set_propagated_clock [all_clocks]
repair_clock_nets
detailed_placement
estimate_parasitics -placement
repair_timing
detailed_placement

# routing
set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_iterations 30 -verbose
detailed_route -output_drc $D/route_drc.rpt -verbose 1
filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
check_placement -verbose

# results
estimate_parasitics -global_routing
report_checks -path_delay max -format full_clock_expanded -group_count 1
report_wns
report_tns
report_design_area
write_def $D/gcd.def
write_verilog -include_pwr_gnd $D/gcd_pnr.v
write_db $D/gcd.odb
exit
