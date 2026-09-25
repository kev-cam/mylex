read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog alu.cmos.v
link_design alu_top
create_clock -name clk -period 4.75 [get_ports clk]
puts "############ SYNTH-ONLY (no buffering, no CTS, no wire RC) @ measured VCD activity"
read_vcd -scope tb/dut alu_synth.vcd
report_power -digits 6
puts "############ SYNTH-ONLY @ alpha=0.5"
set_power_activity -global -activity 0.5 -duty 0.5
report_power -digits 6
