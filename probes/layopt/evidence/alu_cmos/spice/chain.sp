4-cell interconnected chain: validates that per-cell characterisation COMPOSES
* (includes real slew degradation between stages), SPICE vs liberty.
* in -> inv_1 -> nand2_1(B=1) -> nor2_1(B=0) -> inv_1 -> CL=4fF
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VVDD vdd 0 {VDDV}
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* input slew 64.9 ps 20-80% -> 108.17 ps 0-100%
VA n0 0 PULSE(0 {VDDV} 1n 108.1667p 108.1667p 2n 4n)
X1 n1 n0        vdd vss sg13g2_inv_1
X2 n2 n1 nhi    vdd vss sg13g2_nand2_1
X3 n3 n2 nlo    vdd vss sg13g2_nor2_1
X4 n4 n3        vdd vss sg13g2_inv_1
CL n4 0 4f
.tran 2p 5n
.measure tran QCHAIN INTEG I(VVDD) FROM=0.9n TO=4.9n
.measure tran VX MAX V(n4) FROM=0.9n TO=4.9n
.measure tran VN MIN V(n4) FROM=0.9n TO=4.9n
.options timeint reltol=1e-4 abstol=1e-12
.end
