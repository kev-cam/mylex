current_design alu_top
set clk_port [get_ports clk]
create_clock -name core_clock -period 2.0 $clk_port
create_clock -name vclk_core_clock -period 2.0
set_clock_latency 0.290 [get_clocks core_clock]
set_clock_latency 0.290 [get_clocks vclk_core_clock]
set_input_delay 0.4 -clock vclk_core_clock [all_inputs -no_clocks]
set_output_delay 0.4 -clock vclk_core_clock [all_outputs]
