sg13g2_inv_1 with the PDK's OWN PSP103 (103.8.2) verilog-a, vs the 103.4.0 build used so far.
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_orig.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
.param CL=9.34f
VVDD vdd 0 {VDDV}
VVSS vss 0 0
VA a 0 PULSE(0 {VDDV} 1n 108.1667p 108.1667p 2n 4n)
XI1 y a vdd vss sg13g2_inv_1
CLOAD y 0 {CL}
.tran 2p 5n
.measure tran QCYC INTEG I(VVDD) FROM=0.9n TO=4.9n
.measure tran VX MAX V(y) FROM=0.9n TO=4.9n
.measure tran VN MIN V(y) FROM=0.9n TO=4.9n
.measure tran TPHL TRIG V(a) VAL=0.6 RISE=1 TARG V(y) VAL=0.6 FALL=1
.measure tran TPLH TRIG V(a) VAL=0.6 FALL=1 TARG V(y) VAL=0.6 RISE=1
.options timeint reltol=1e-4 abstol=1e-12
.end
