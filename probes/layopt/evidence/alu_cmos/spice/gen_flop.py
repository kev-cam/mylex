#!/usr/bin/env python3
"""Xyce deck: sg13g2_dfrbpq_1 energy per CLOCK CYCLE, at the ALU's own load and slews.
Two cases give a linear decomposition:
  A: D static  -> clock-only floor (the term async/QAL claim to remove)
  B: D toggles every cycle -> Q toggles every cycle (alpha=1)
  E_cycle(alpha) = E_A + alpha*(E_B - E_A)
Measured design values: CL=8.11 fF, CLK slew 20.1 ps, D slew 50.0 ps, alpha_Q=alpha_D=0.3701
"""
import sys
SHIM=sys.argv[1]; OUT=sys.argv[2]
VDD=1.2; T=4.75e-9; CL="8.11f"
TRC=20.1/0.6; TRD=50.0/0.6          # ps, liberty slew 20-80% -> 0-100% ramp
NC=22; TSTART=2*T; TEND=NC*T
L=[f"sg13g2_dfrbpq_1 energy/cycle at ALU load+slew (SG13G2, PSP103)",
   '.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"',
   '.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"',
   f'.include "{SHIM}"',
   '.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"',
   f".param VDDV={VDD}",
   "VHI nhi 0 {VDDV}", "VSSG vss 0 0",
   f"* clock: period {T*1e9} ns, 20-80%% slew 20.1 ps",
   f"VCLK clk 0 PULSE(0 {{VDDV}} 0.5n {TRC:.4f}p {TRC:.4f}p {T*1e9/2-TRC*1e-3:.6f}n {T*1e9:.6f}n)",
   f"* D toggling every clock cycle (alpha=1): period = 2*T",
   f"VDT dt 0 PULSE(0 {{VDDV}} 1.0n {TRD:.4f}p {TRD:.4f}p {T*1e9-TRD*1e-3:.6f}n {2*T*1e9:.6f}n)",
   "* --- case A: D static low (clock-only floor)",
   "VAdd avdd 0 {VDDV}",
   f"XA aq clk 0 nhi avdd vss sg13g2_dfrbpq_1",
   f"CA aq 0 {CL}",
   "* --- case A2: D static HIGH (checks the static-D level does not matter)",
   "VA2dd a2vdd 0 {VDDV}",
   f"XA2 a2q clk nhi nhi a2vdd vss sg13g2_dfrbpq_1",
   f"CA2 a2q 0 {CL}",
   "* --- case B: Q toggles every cycle",
   "VBdd bvdd 0 {VDDV}",
   f"XB bq clk dt nhi bvdd vss sg13g2_dfrbpq_1",
   f"CB bq 0 {CL}",
   f".measure tran QA  INTEG I(VAdd)  FROM={TSTART*1e9}n TO={TEND*1e9}n",
   f".measure tran QA2 INTEG I(VA2dd) FROM={TSTART*1e9}n TO={TEND*1e9}n",
   f".measure tran QB  INTEG I(VBdd)  FROM={TSTART*1e9}n TO={TEND*1e9}n",
   f"* Q toggle count check",
   f".print tran format=noindex V(clk) V(dt) V(aq) V(bq)",
   f".tran 2p {TEND*1e9}n",
   ".options timeint reltol=1e-4 abstol=1e-12",
   ".end"]
open(OUT,'w').write('\n'.join(L)+'\n')
print("wrote",OUT," cycles measured =",NC-2)
