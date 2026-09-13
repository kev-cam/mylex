set P /home/claude/tools/orfs-sky130hd
set D /home/claude/src/alu-flow/hints
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_liberty $P/sky130_fd_sc_hd__tt_025C_1v80.lib
read_def $D/alu_base.def
read_sdc /home/claude/src/alu-flow/constraint.sdc
source $P/setRC.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
report_checks -path_delay max -fields {input_net slew cap fanout} -format full_clock_expanded -group_count 3 > $D/sta_worst.rpt
report_checks -path_delay max -unconstrained -fields {input_net slew cap fanout} -group_count 5 -endpoint_count 1 -unique_paths_to_endpoint >> $D/sta_worst.rpt
exit
