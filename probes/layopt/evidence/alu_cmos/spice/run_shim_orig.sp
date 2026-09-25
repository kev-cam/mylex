sg13g2_inv_1 E(CL) slope check
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_orig.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
.param CL=2f
.param TSL=20p
VVDD vdd 0 {VDDV}
VVSS vss 0 0
VA a 0 PULSE(0 {VDDV} 1n {TSL} {TSL} 2n 4n)
XI1 y a vdd vss sg13g2_inv_1
CLOAD y 0 {CL}
.step CL LIST 0.001f 2f 5f 10f 20f
.tran 1p 5n
.measure tran QCYC INTEG I(VVDD) FROM=0.9n TO=4.9n
.measure tran QRISE INTEG I(VVDD) FROM=0.9n TO=2.9n
.measure tran QFALL INTEG I(VVDD) FROM=2.9n TO=4.9n
.measure tran TPHL TRIG V(a) VAL={VDDV/2} RISE=1 TARG V(y) VAL={VDDV/2} FALL=1
.measure tran TPLH TRIG V(a) VAL={VDDV/2} FALL=1 TARG V(y) VAL={VDDV/2} RISE=1
.options timeint reltol=1e-5 abstol=1e-12
.end
