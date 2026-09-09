# layopt: route the dissolved placement -- merged cells as LEF macros, the row's cells where the dissolve left them
set P /home/claude/tools/orfs-sky130hd
set D /home/claude/src/gcd-flow/hints
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_lef $D/merged.lef
read_def $D/merged.def
set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_iterations 30 -verbose
detailed_route -output_drc $D/route_drc_merged.rpt -verbose 1
write_def $D/gcd_merged_routed.def
exit
