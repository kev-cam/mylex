# alu_top timing constraints — relaxed 10ns clock (geometry run, not timing closure)
current_design alu_top
create_clock -name clk -period 10.0 [get_ports clk]
set_clock_uncertainty 0.25 [get_clocks clk]
set non_clock_inputs [all_inputs -no_clocks]
set_input_delay  2.0 -clock clk $non_clock_inputs
set_output_delay 2.0 -clock clk [all_outputs]
set_driving_cell -lib_cell sky130_fd_sc_hd__inv_2 -pin Y $non_clock_inputs
set_load 0.02 [all_outputs]
