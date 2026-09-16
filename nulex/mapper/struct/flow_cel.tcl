read_lef /home/claude/tools/orfs-sky130hd/sky130_fd_sc_hd.tlef
read_lef /home/claude/tools/orfs-sky130hd/sky130_fd_sc_hd_merged.lef
read_liberty /home/claude/tools/orfs-sky130hd/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog cel_demo.v
link_design cel_demo
source /home/claude/tools/orfs-sky130hd/setRC.tcl
initialize_floorplan -utilization 30 -aspect_ratio 1 -core_space 2.0 -site unithd
source /home/claude/tools/orfs-sky130hd/make_tracks.tcl
set ::env(TAP_CELL_NAME) sky130_fd_sc_hd__tapvpwrvgnd_1
source /home/claude/tools/orfs-sky130hd/tapcell.tcl
add_global_connection -net VDD -pin_pattern VPWR -power
add_global_connection -net VDD -pin_pattern VPB
add_global_connection -net VSS -pin_pattern VGND -ground
add_global_connection -net VSS -pin_pattern VNB
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name grid -voltage_domains CORE
add_pdn_stripe -grid grid -layer met1 -width 0.48 -pitch 5.44 -offset 0 -followpins
pdngen
global_placement -skip_io -density 0.55
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.55
detailed_placement
set_routing_layers -signal met1-met5
global_route -congestion_iterations 30
detailed_route -output_drc cel_drc.rpt -verbose 1
check_placement
report_design_area
write_def cel_demo.def
puts "cel-flow: DONE (C-element feedback loops routed)"
exit
