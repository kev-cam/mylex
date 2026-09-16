# OpenROAD P&R of a structural threshold-gate netlist on the TH-cell physical
# views (nulex/lib/th_pdk, derived from sky130). Combinational (no CTS).
set P /home/claude/tools/orfs-sky130hd
set D [file dirname [file normalize [info script]]]
set TH $D/../../lib/th_pdk
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_lef $TH/th_cells.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_liberty $TH/th_cells.lib
read_verilog $D/add4_th_clean.v
link_design add4
source $P/setRC.tcl
initialize_floorplan -utilization 40 -aspect_ratio 1 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
set ::env(TAP_CELL_NAME) sky130_fd_sc_hd__tapvpwrvgnd_1
source $P/tapcell.tcl
source $P/pdn.tcl
pdngen
global_placement -skip_io -density 0.60 -pad_left 1 -pad_right 1
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.60 -pad_left 1 -pad_right 1
detailed_placement
optimize_mirroring
set_routing_layers -signal met1-met5
global_route -congestion_iterations 30
detailed_route -output_drc $D/th_route_drc.rpt -verbose 1
filler_placement {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
check_placement -verbose
report_design_area
write_def $D/add4_th.def
puts "th-flow: DONE -> add4_th.def"
exit
