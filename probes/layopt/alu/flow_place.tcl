# layopt: sky130hd place-and-route of gcd with OpenROAD (standalone Tcl, no ORFS make)
set P /home/claude/tools/orfs-sky130hd
set D /home/claude/src/alu-flow/hints
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog /home/claude/src/alu-flow/alu_synth.v
link_design alu_top
read_sdc /home/claude/src/alu-flow/constraint.sdc
source $P/setRC.tcl
set_dont_use {sky130_fd_sc_hd__probe_p_8 sky130_fd_sc_hd__probec_p_8 sky130_fd_sc_hd__lpflow_* sky130_fd_sc_hd__clkinvlp_*}

# floorplan
initialize_floorplan -utilization 33 -aspect_ratio 1 -core_space 2.0 -site unithd
source $P/make_tracks.tcl
set ::env(TAP_CELL_NAME) sky130_fd_sc_hd__tapvpwrvgnd_1
source $P/tapcell.tcl
source $P/pdn.tcl
pdngen

# placement: io-less placement first, then pins, then the real placement
global_placement -skip_io -density 0.60 -pad_left 2 -pad_right 2
place_pins -hor_layers met3 -ver_layers met2
global_placement -density 0.60 -pad_left 2 -pad_right 2
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

# pre-route hand-off point: the placement the router would see
write_def $D/alu_placed.def
write_db $D/alu_placed.odb
exit
