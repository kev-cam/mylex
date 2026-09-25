read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t9
create_clock -name vclk -period 4.75
set_load 0.00566 [get_nets o]
set_input_transition 0.0756 [all_inputs]
set_power_activity -input_port S -activity 1.0 -duty 0.5
set_power_activity -input_port A0 -activity 0.0 -duty 0.0
set_power_activity -input_port A1 -activity 0.0 -duty 1.0
puts "@@@CELL sg13g2_mux2_1 arc=S->X CL=5.66 slew=75.6"
report_power -digits 9
report_power -instances [get_cells u0] -digits 9
