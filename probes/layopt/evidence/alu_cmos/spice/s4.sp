ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c4: sg13g2_nand2_1 arc A->Y  CL=4.93fF  slew20-80=86.2ps (tr=143.7ps)
Vc4dd c4vdd 0 {VDDV}
Vc4in c4in 0 PULSE(0 {VDDV} 1n 143.6667p 143.6667p 2n 4n)
Xc4 c4out c4in nhi c4vdd vss sg13g2_nand2_1
Cc4 c4out 0 4.93f
.measure tran Qc4 INTEG I(Vc4dd) FROM=0.9n TO=4.9n
.measure tran VXc4 MAX V(c4out) FROM=0.9n TO=4.9n
.measure tran VNc4 MIN V(c4out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
