read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t6
create_clock -name vclk -period 4.75
set_load 0.00426 [get_nets o]
set_input_transition 0.08070000000000001 [all_inputs]
set_power_activity -input_port A1 -activity 1.0 -duty 0.5
set_power_activity -input_port A2 -activity 0.0 -duty 0.0
set_power_activity -input_port B1 -activity 0.0 -duty 1.0
puts "@@@CELL sg13g2_o21ai_1 arc=A1->Y CL=4.26 slew=80.7"
report_power -digits 9
report_power -instances [get_cells u0] -digits 9
