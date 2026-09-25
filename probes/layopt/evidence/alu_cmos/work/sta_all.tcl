read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog alu.cmos.v
link_design alu_top
create_clock -name clk -period 10 [get_ports clk]
set_input_delay 0 -clock clk [all_inputs -no_clocks]
set_output_delay 0 -clock clk [all_outputs]
puts "=========== REG-TO-REG (max), top 3 ==========="
report_checks -path_delay max -from [all_registers] -to [all_registers] -group_count 3 -digits 4
puts "=========== ALL PATHS (max), top 1 ==========="
report_checks -path_delay max -group_count 1 -digits 4
puts "=========== WNS/TNS ==========="
report_wns -digits 4
report_tns -digits 4
puts "=========== AREA ==========="
report_design_area
