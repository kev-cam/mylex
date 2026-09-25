read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t1
create_clock -name vclk -period 4.75
set_load 0.02168 [get_nets o]
set_input_transition 0.0722 [all_inputs]
set_power_activity -input_port A -activity 1.0 -duty 0.5
puts "@@@CELL sg13g2_buf_1 arc=A->X CL=21.68 slew=72.2"
report_power -digits 9
report_power -instances [get_cells u0] -digits 9
