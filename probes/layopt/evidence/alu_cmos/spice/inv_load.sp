sg13g2_inv_1 E(CL) at the ALU's real input slew (64.9ps liberty -> 108.2ps 0-100% ramp)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
.param CL=2f
VVDD vdd 0 {VDDV}
VVSS vss 0 0
VA a 0 PULSE(0 {VDDV} 1n 108.1667p 108.1667p 2n 4n)
XI1 y a vdd vss sg13g2_inv_1
CLOAD y 0 {CL}
.step CL LIST 1f 2f 4.26f 9.34f 15f 23.4f 39f
.tran 2p 5n
.measure tran QCYC INTEG I(VVDD) FROM=0.9n TO=4.9n
.measure tran VX MAX V(y) FROM=0.9n TO=4.9n
.measure tran VN MIN V(y) FROM=0.9n TO=4.9n
.measure tran TPHL TRIG V(a) VAL=0.6 RISE=1 TARG V(y) VAL=0.6 FALL=1
.measure tran TPLH TRIG V(a) VAL=0.6 FALL=1 TARG V(y) VAL=0.6 RISE=1
.options timeint reltol=1e-4 abstol=1e-12
.end
