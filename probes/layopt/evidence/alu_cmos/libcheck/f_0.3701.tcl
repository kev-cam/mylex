read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog flop.v
link_design tf
create_clock -name clk -period 4.75 [get_ports clk]
set_load 0.00811 [get_nets q]
set_input_transition 0.0201 [get_ports clk]
set_input_transition 0.0500 [get_ports d]
set_input_transition 0.0201 [get_ports rb]
set_power_activity -input_port d -activity 0.3701 -duty 0.5
set_power_activity -input_port rb -activity 0.0 -duty 1.0
puts "@@@FLOP alpha=0.3701"
report_power -digits 9
