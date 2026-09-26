set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
set LIB $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
set P $::env(CLKP)
read_lef $PDK/libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef
read_lef $PDK/libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef
read_liberty $LIB
read_verilog exec.cmos.v
link_design exec_top
source constraints.tcl
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
initialize_floorplan -utilization 45 -aspect_ratio 1.0 -core_space 5.0 -site CoreSite
source tracks.tcl
place_pins -hor_layers Metal3 -ver_layers Metal2
# yosys emits 1'h1 on all 188 flop RESET_B pins; without tie cells OpenROAD writes
# that as an UNDRIVEN net 'one_' -> every flop is X in gate sim. Tie cells per PDK
# librelane config.tcl (SYNTH_TIEHI_PORT/SYNTH_TIELO_PORT).
insert_tiecells sg13g2_tiehi/L_HI -prefix TIEHI_
insert_tiecells sg13g2_tielo/L_LO -prefix TIELO_
global_placement -density 0.55
estimate_parasitics -placement
puts "########## REPAIR_DESIGN (DRV) ##########"
repair_design
estimate_parasitics -placement
puts "########## REPAIR_TIMING -setup (pre-CTS) ##########"
repair_timing -setup
detailed_placement
estimate_parasitics -placement
puts "########## CTS ##########"
set_wire_rc -clock -layer Metal5
clock_tree_synthesis -root_buf sg13g2_buf_16 -buf_list {sg13g2_buf_8 sg13g2_buf_4 sg13g2_buf_2} \
    -sink_clustering_enable -sink_clustering_size 20 -sink_clustering_max_diameter 60
set_propagated_clock [all_clocks]
detailed_placement
estimate_parasitics -placement
puts "########## REPAIR_TIMING -setup (post-CTS) ##########"
repair_timing -setup
repair_timing -hold -hold_margin 0.05
detailed_placement
estimate_parasitics -placement
puts "########## FINAL ##########"
report_check_types -max_fanout -max_capacitance -max_slew -violators
report_checks -path_delay max -group_path_count 1 -digits 4
report_checks -path_delay min -group_path_count 1 -digits 4
report_clock_skew -digits 4
report_wns -digits 4
report_tns -digits 4
report_design_area
report_cell_usage
write_verilog exec.phys_$P.v
write_db exec.phys_$P.odb
