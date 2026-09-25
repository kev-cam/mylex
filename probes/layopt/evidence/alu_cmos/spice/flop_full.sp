sg13g2_dfrbpq_1 energy/cycle at ALU load+slew (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VSSG vss 0 0
* clock: period 4.75 ns, 20-80%% slew 20.1 ps
VCLK clk 0 PULSE(0 {VDDV} 0.5n 33.5000p 33.5000p 2.341500n 4.750000n)
* D toggling every clock cycle (alpha=1): period = 2*T
VDT dt 0 PULSE(0 {VDDV} 1.0n 83.3333p 83.3333p 4.666667n 9.500000n)
* --- case A: D static low (clock-only floor)
VAdd avdd 0 {VDDV}
XA aq clk 0 nhi avdd vss sg13g2_dfrbpq_1
CA aq 0 8.11f
* --- case A2: D static HIGH (checks the static-D level does not matter)
VA2dd a2vdd 0 {VDDV}
XA2 a2q clk nhi nhi a2vdd vss sg13g2_dfrbpq_1
CA2 a2q 0 8.11f
* --- case B: Q toggles every cycle
VBdd bvdd 0 {VDDV}
XB bq clk dt nhi bvdd vss sg13g2_dfrbpq_1
CB bq 0 8.11f
.measure tran QA  INTEG I(VAdd)  FROM=9.5n TO=104.5n
.measure tran QA2 INTEG I(VA2dd) FROM=9.5n TO=104.5n
.measure tran QB  INTEG I(VBdd)  FROM=9.5n TO=104.5n
* Q toggle count check
.print tran format=noindex V(clk) V(dt) V(aq) V(bq)
.tran 2p 104.5n
.options timeint reltol=1e-4 abstol=1e-12
.end
