sg13g2_inv_1 energy/delay anchor check vs campaign value 10.08 fJ/op, 34.81 ps @ 2fF
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"

.param VDDV=1.2
.param CL=2f
.param TSL=20p

VVDD vdd 0 {VDDV}
VVSS vss 0 0
* input: one rise at 1n, one fall at 3n
VA a 0 PULSE(0 {VDDV} 1n {TSL} {TSL} 2n 4n)
XI1 y a vdd vss sg13g2_inv_1
CLOAD y 0 {CL}

.tran 1p 5n
* charge drawn from VDD over the full rise+fall cycle
.measure tran QCYC INTEG I(VVDD) FROM=0.9n TO=4.9n
.measure tran QRISE INTEG I(VVDD) FROM=0.9n TO=2.9n
.measure tran QFALL INTEG I(VVDD) FROM=2.9n TO=4.9n
* propagation delays (inverter: input rise -> output fall)
.measure tran TPHL TRIG V(a) VAL={VDDV/2} RISE=1 TARG V(y) VAL={VDDV/2} FALL=1
.measure tran TPLH TRIG V(a) VAL={VDDV/2} FALL=1 TARG V(y) VAL={VDDV/2} RISE=1
.measure tran VYHI MAX V(y) FROM=4.5n TO=4.9n
.measure tran VYLO MIN V(y) FROM=2.0n TO=2.8n
.print tran format=noindex V(a) V(y) I(VVDD)
.options timeint reltol=1e-5 abstol=1e-12
.end
