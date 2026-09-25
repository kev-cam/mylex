ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c0: sg13g2_inv_1 arc A->Y  CL=9.34fF  slew20-80=64.9ps (tr=108.2ps)
Vc0dd c0vdd 0 {VDDV}
Vc0in c0in 0 PULSE(0 {VDDV} 1n 108.1667p 108.1667p 2n 4n)
Xc0 c0out c0in c0vdd vss sg13g2_inv_1
Cc0 c0out 0 9.34f
.measure tran Qc0 INTEG I(Vc0dd) FROM=0.9n TO=4.9n
* ---- c1: sg13g2_buf_1 arc A->X  CL=21.68fF  slew20-80=72.2ps (tr=120.3ps)
Vc1dd c1vdd 0 {VDDV}
Vc1in c1in 0 PULSE(0 {VDDV} 1n 120.3333p 120.3333p 2n 4n)
Xc1 c1out c1in c1vdd vss sg13g2_buf_1
Cc1 c1out 0 21.68f
.measure tran Qc1 INTEG I(Vc1dd) FROM=0.9n TO=4.9n
* ---- c4: sg13g2_nand2_1 arc A->Y  CL=4.93fF  slew20-80=86.2ps (tr=143.7ps)
Vc4dd c4vdd 0 {VDDV}
Vc4in c4in 0 PULSE(0 {VDDV} 1n 143.6667p 143.6667p 2n 4n)
Xc4 c4out c4in nhi c4vdd vss sg13g2_nand2_1
Cc4 c4out 0 4.93f
.measure tran Qc4 INTEG I(Vc4dd) FROM=0.9n TO=4.9n
* ---- c5: sg13g2_nor2_1 arc A->Y  CL=4.75fF  slew20-80=87.0ps (tr=145.0ps)
Vc5dd c5vdd 0 {VDDV}
Vc5in c5in 0 PULSE(0 {VDDV} 1n 145.0000p 145.0000p 2n 4n)
Xc5 c5out c5in nlo c5vdd vss sg13g2_nor2_1
Cc5 c5out 0 4.75f
.measure tran Qc5 INTEG I(Vc5dd) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
