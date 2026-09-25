ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c5: sg13g2_nor2_1 arc A->Y  CL=4.75fF  slew20-80=87.0ps (tr=145.0ps)
Vc5dd c5vdd 0 {VDDV}
Vc5in c5in 0 PULSE(0 {VDDV} 1n 145.0000p 145.0000p 2n 4n)
Xc5 c5out c5in nlo c5vdd vss sg13g2_nor2_1
Cc5 c5out 0 4.75f
.measure tran Qc5 INTEG I(Vc5dd) FROM=0.9n TO=4.9n
.measure tran VXc5 MAX V(c5out) FROM=0.9n TO=4.9n
.measure tran VNc5 MIN V(c5out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
