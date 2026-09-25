read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t2
create_clock -name vclk -period 4.75
set_load 0.032869999999999996 [get_nets o]
set_input_transition 0.07890000000000001 [all_inputs]
set_power_activity -input_port A -activity 1.0 -duty 0.5
puts "@@@CELL sg13g2_buf_8 arc=A->X CL=32.87 slew=78.9"
report_power -digits 9
report_power -instances [get_cells u0] -digits 9
