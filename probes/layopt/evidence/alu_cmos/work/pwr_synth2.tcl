read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog alu.cmos.v
link_design alu_top
create_clock -name clk -period 4.75 [get_ports clk]
set_load 0.006 [all_outputs]
read_vcd -scope tb/dut alu_synth.vcd
report_power -digits 6
