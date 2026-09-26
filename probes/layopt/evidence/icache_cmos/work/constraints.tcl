set CLKP $::env(CLKP)
# alu_top SDC. CLK_PERIOD set by caller.
create_clock -name clk -period $CLKP [get_ports clk]
set_input_delay  [expr $CLKP*0.10] -clock clk [all_inputs -no_clocks]
set_output_delay [expr $CLKP*0.10] -clock clk [all_outputs]
# librelane sg13g2_stdcell/config.tcl defaults
set_driving_cell -lib_cell sg13g2_buf_4 -pin X [all_inputs -no_clocks]
set_load [expr 6.0/1000.0] [all_outputs]        ;# OUTPUT_CAP_LOAD 6.0 fF -> pF
set_max_fanout 10 [current_design]              ;# MAX_FANOUT_CONSTRAINT 10
set_clock_uncertainty 0.25 [get_clocks clk]     ;# CLOCK_UNCERTAINTY_CONSTRAINT
set_clock_transition 0.15 [get_clocks clk]      ;# CLOCK_TRANSITION_CONSTRAINT
