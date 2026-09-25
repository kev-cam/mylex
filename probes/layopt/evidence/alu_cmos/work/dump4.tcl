set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
create_clock -name clk -period 4.75 [get_ports clk]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
set fh [open esc_nets.txt r]
while {[gets $fh nm] >= 0} { puts "@@@N $nm"; if {[catch {report_net -digits 6 $nm} e]} { puts "FAIL $e" } }
close $fh
