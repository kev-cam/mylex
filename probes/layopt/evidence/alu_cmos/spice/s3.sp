ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c3: sg13g2_buf_16 arc A->X  CL=26.28fF  slew20-80=33.6ps (tr=56.0ps)
Vc3dd c3vdd 0 {VDDV}
Vc3in c3in 0 PULSE(0 {VDDV} 1n 56.0000p 56.0000p 2n 4n)
Xc3 c3out c3in c3vdd vss sg13g2_buf_16
Cc3 c3out 0 26.28f
.measure tran Qc3 INTEG I(Vc3dd) FROM=0.9n TO=4.9n
.measure tran VXc3 MAX V(c3out) FROM=0.9n TO=4.9n
.measure tran VNc3 MIN V(c3out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
