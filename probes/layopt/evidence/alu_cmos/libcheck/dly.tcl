read_liberty /usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_verilog cells.v
link_design t0
create_clock -name vclk -period 4.75
set_load 0.00934 [get_nets o]
set_input_transition 0.0649 [get_ports A]
set_input_delay 0 -clock vclk [all_inputs]
set_output_delay 0 -clock vclk [all_outputs]
report_checks -from A -to o -path_delay max -digits 5 -fields {slew}
report_checks -from A -to o -path_delay min -digits 5 -fields {slew}
