set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
create_clock -name clk -period 4.75 [get_ports clk]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
report_net _3000_
puts "=== props of a net:"
puts [get_property [get_nets _3000_] object_type]
