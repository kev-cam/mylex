set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
create_clock -name clk -period 4.75 [get_ports clk]
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
read_vcd -scope tb/dut alu_phys.vcd
set out [open inst_power.json w]
puts $out [report_power -instances [get_cells *] -format json -digits 9]
close $out
# per-net total capacitance (pin caps + estimated wire cap)
set fh [open net_cap.txt w]
foreach n [get_nets *] {
  set nm [get_name $n]
  if {[catch {set c [get_property $n capacitance]}]} { set c -1 }
  puts $fh "$nm $c"
}
close $fh
puts "nets: [llength [get_nets *]]  cells: [llength [get_cells *]]"
