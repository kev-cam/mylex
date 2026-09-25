read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t0
create_clock -name vclk -period 4.75
set_load 0.039 [get_nets o]
set_input_transition 0.0649 [all_inputs]
set_power_activity -input_port A -activity 1.0 -duty 0.5
report_power -digits 12
