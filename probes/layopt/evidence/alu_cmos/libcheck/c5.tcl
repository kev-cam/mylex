read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t5
create_clock -name vclk -period 4.75
set_load 0.00475 [get_nets o]
set_input_transition 0.087 [all_inputs]
set_power_activity -input_port A -activity 1.0 -duty 0.5
set_power_activity -input_port B -activity 0.0 -duty 0.0
puts "@@@CELL sg13g2_nor2_1 arc=A->Y CL=4.75 slew=87.0"
report_power -digits 9
report_power -instances [get_cells u0] -digits 9
