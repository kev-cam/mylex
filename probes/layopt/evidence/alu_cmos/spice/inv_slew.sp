sg13g2_inv_1 internal energy vs INPUT SLEW at fixed CL=9.34fF.
* Separates short-circuit current (vanishes at fast edges) from self-capacitance.
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
.param TSL=108.1667p
VVDD vdd 0 {VDDV}
VVSS vss 0 0
VA a 0 PULSE(0 {VDDV} 1n {TSL} {TSL} 2n 4n)
XI1 y a vdd vss sg13g2_inv_1
CLOAD y 0 9.34f
.step TSL LIST 2p 10p 30p 108.1667p 300p 800p
.tran 1p 5n
.measure tran QCYC INTEG I(VVDD) FROM=0.9n TO=4.9n
.measure tran VX MAX V(y) FROM=0.9n TO=4.9n
.measure tran VN MIN V(y) FROM=0.9n TO=4.9n
.options timeint reltol=1e-4 abstol=1e-13
.end
