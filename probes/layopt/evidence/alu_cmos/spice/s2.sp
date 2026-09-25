ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c2: sg13g2_buf_8 arc A->X  CL=32.87fF  slew20-80=78.9ps (tr=131.5ps)
Vc2dd c2vdd 0 {VDDV}
Vc2in c2in 0 PULSE(0 {VDDV} 1n 131.5000p 131.5000p 2n 4n)
Xc2 c2out c2in c2vdd vss sg13g2_buf_8
Cc2 c2out 0 32.87f
.measure tran Qc2 INTEG I(Vc2dd) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
