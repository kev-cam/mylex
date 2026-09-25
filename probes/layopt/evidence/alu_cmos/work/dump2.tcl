set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
create_clock -name clk -period 4.75 [get_ports clk]
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
puts "@@@NETCAPS"
foreach n [get_nets *] { set nm [get_name $n]; puts "@@@N $nm"; catch {report_net -digits 6 $nm} }
puts "@@@ENDNETCAPS"
