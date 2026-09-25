set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db alu.phys_4.75.odb
create_clock -name clk -period 4.75 [get_ports clk]
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement
foreach inst [get_cells *] {
  set ref [get_property $inst ref_name]
  foreach p [get_pins -of_objects $inst] {
    if {[get_property $p direction] ne "input"} continue
    set r ""; set f ""
    catch {set r [get_property $p slew_max_rise]}
    catch {set f [get_property $p slew_max_fall]}
    puts "SLEW $ref [get_name $p] $r $f"
  }
}
