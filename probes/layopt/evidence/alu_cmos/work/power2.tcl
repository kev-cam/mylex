set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
set CLKP 4.75
source constraints.tcl
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
puts "###### WITH 6fF output loads (librelane OUTPUT_CAP_LOAD), measured VCD"
read_vcd -scope tb/dut alu_phys.vcd
report_power -digits 6
puts "###### alpha=0.5"
set_power_activity -global -activity 0.5 -duty 0.5
report_power -digits 6
