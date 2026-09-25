ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c9: sg13g2_mux2_1 arc S->X  CL=5.66fF  slew20-80=75.6ps (tr=126.0ps)
Vc9dd c9vdd 0 {VDDV}
Vc9in c9in 0 PULSE(0 {VDDV} 1n 126.0000p 126.0000p 2n 4n)
Xc9 c9out nlo nhi c9in c9vdd vss sg13g2_mux2_1
Cc9 c9out 0 5.66f
.measure tran Qc9 INTEG I(Vc9dd) FROM=0.9n TO=4.9n
.measure tran VXc9 MAX V(c9out) FROM=0.9n TO=4.9n
.measure tran VNc9 MIN V(c9out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
