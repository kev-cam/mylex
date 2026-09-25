ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c7: sg13g2_a21oi_1 arc A1->Y  CL=4.99fF  slew20-80=81.4ps (tr=135.7ps)
Vc7dd c7vdd 0 {VDDV}
Vc7in c7in 0 PULSE(0 {VDDV} 1n 135.6667p 135.6667p 2n 4n)
Xc7 c7out c7in nhi nlo c7vdd vss sg13g2_a21oi_1
Cc7 c7out 0 4.99f
.measure tran Qc7 INTEG I(Vc7dd) FROM=0.9n TO=4.9n
.measure tran VXc7 MAX V(c7out) FROM=0.9n TO=4.9n
.measure tran VNc7 MIN V(c7out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
