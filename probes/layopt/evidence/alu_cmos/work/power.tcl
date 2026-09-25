set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
set CLKP 4.75
create_clock -name clk -period $CLKP [get_ports clk]
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
puts "################ POWER @ MEASURED VCD ACTIVITY ################"
read_power_activities -scope tb/dut alu_phys.vcd
report_power -digits 6
puts "################ POWER @ alpha=0.5 (duty 0.5) ################"
set_power_activity -global -activity 0.5 -duty 0.5
report_power -digits 6
puts "################ POWER @ alpha=1.0 (duty 0.5) ################"
set_power_activity -global -activity 1.0 -duty 0.5
report_power -digits 6
