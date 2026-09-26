# Two-activity, NO-VCD power method for the E_tree(N) / E0_ff(N) scaling
# campaign. VALIDATED against the alu_cmos anchor's VCD-derived numbers:
#   E_tree 44.333 vs 44.334 fJ/flop/cyc (-0.001%), E0_ff 59.055 vs 59.106 (-0.087%)
#   (validation log: alu_cmos/work/pwr_novcd_validation.log)
#
# Usage:  ODB=<block>.phys_4.75.odb CLKP=4.75 openroad -no_init -exit pwr_novcd.tcl
# Then:   Clock group total power     -> E_tree = P_clk*T/Nff  (same at ALL
#         activities = activity-independence check; if it varies, STOP)
#         Sequential group at a=0.0   -> E0_ff  = P_seq(0)*T/Nff
#         Sequential at 0.2/1.0       -> data-dependent seq slope (context only)
#
# METHOD NOTES (each one was a measured failure mode, not a style choice):
# 1. DO NOT use `set_power_activity -global`: in OpenSTA it takes precedence
#    over every per-pin annotation, so tie-high flop RESET_B nets get duty 0.5
#    and the flop CLK-pin internal power averages half its weight from the
#    liberty !RESET_B (in-reset) when-tables -> E0_ff comes out 13.8% LOW
#    (50.95 vs 59.11 fJ; single-cell check: rb duty 1.0 -> 12.493 uW = the
#    anchor reference exactly, rb duty 0.5 -> 10.786 uW). Set ALL instance
#    pins explicitly, then override the tie nets.
# 2. Flop CLK pins keep origin "clock" (2 transitions/cycle) regardless of the
#    pin annotations -- that is what makes the Clock group and the a=0
#    Sequential floor activity-independent.
# 3. The a=0 "floor" run is the E0_ff measurement. With the tie duties
#    corrected the Sequential group is exactly linear in activity on the
#    anchor (extrapolating 0.2/1.0 to zero reproduces the direct a=0 run to 7
#    digits: 2.337323 mW); WITHOUT the tie fix it is convex and extrapolation
#    lands ~2% high on a 13.8%-low floor. Report the direct a=0 run as E0_ff
#    and quote the 0.2/1.0 extrapolation as the linearity cross-check.
set PDK /usr/local/src/IHP-Open-PDK/ihp-sg13g2
read_liberty $PDK/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib
read_db $::env(ODB)
set CLKP $::env(CLKP)
create_clock -name clk -period $CLKP [get_ports clk]
set_propagated_clock [all_clocks]
source /home/claude/tools/OpenROAD/test/ihp-sg13g2/setRC.tcl
estimate_parasitics -placement

set NFF [llength [get_cells -filter {ref_name == sg13g2_dfrbpq_1}]]
# anchor bookkeeping counted 53 CTS cells = 49 clkbuf_* + 4 clkload* — count both
set NCLKBUF [llength [get_cells -quiet clkbuf_*]]
set NCLKLD [llength [get_cells -quiet clkload*]]
puts "NFF(dfrbpq_1)=$NFF  CTS_cells=[expr {$NCLKBUF+$NCLKLD}] (clkbuf=$NCLKBUF clkload=$NCLKLD)  CLKP=$CLKP"

set allpins [get_pins *]
foreach A {0.0 0.2 1.0} {
  set_power_activity -pins $allpins -activity $A -duty 0.5
  set_power_activity -input -activity $A -duty 0.5
  # ties / async-reset nets sit quiet at their tied value in real operation
  set hi [get_pins -quiet TIEHI_*/L_HI]
  if {[llength $hi]} { set_power_activity -pins $hi -activity 0.0 -duty 1.0 }
  set lo [get_pins -quiet TIELO_*/L_LO]
  if {[llength $lo]} { set_power_activity -pins $lo -activity 0.0 -duty 0.0 }
  set rb [get_pins -quiet */RESET_B]
  if {[llength $rb]} { set_power_activity -pins $rb -activity 0.0 -duty 1.0 }
  puts "################ NOVCD POWER @ alpha=$A (duty 0.5, ties duty-corrected) ################"
  report_power -digits 6
}
