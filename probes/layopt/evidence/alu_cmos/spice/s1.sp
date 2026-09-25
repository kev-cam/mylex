ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c1: sg13g2_buf_1 arc A->X  CL=21.68fF  slew20-80=72.2ps (tr=120.3ps)
Vc1dd c1vdd 0 {VDDV}
Vc1in c1in 0 PULSE(0 {VDDV} 1n 120.3333p 120.3333p 2n 4n)
Xc1 c1out c1in c1vdd vss sg13g2_buf_1
Cc1 c1out 0 21.68f
.measure tran Qc1 INTEG I(Vc1dd) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
