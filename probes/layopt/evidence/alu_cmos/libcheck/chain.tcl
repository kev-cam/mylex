read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog chain.v
link_design chain
create_clock -name vclk -period 4.75
set_load 0.004 [get_nets n4]
set_input_transition 0.0649 [get_ports n0]
set_power_activity -input_port n0 -activity 1.0 -duty 0.5
set_power_activity -input_port hi -activity 0.0 -duty 1.0
set_power_activity -input_port lo -activity 0.0 -duty 0.0
report_power -digits 9
