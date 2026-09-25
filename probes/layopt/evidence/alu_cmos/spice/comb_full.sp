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
* ---- c2: sg13g2_buf_8 arc A->X  CL=32.87fF  slew20-80=78.9ps (tr=131.5ps)
Vc2dd c2vdd 0 {VDDV}
Vc2in c2in 0 PULSE(0 {VDDV} 1n 131.5000p 131.5000p 2n 4n)
Xc2 c2out c2in c2vdd vss sg13g2_buf_8
Cc2 c2out 0 32.87f
.measure tran Qc2 INTEG I(Vc2dd) FROM=0.9n TO=4.9n
* ---- c3: sg13g2_buf_16 arc A->X  CL=26.28fF  slew20-80=33.6ps (tr=56.0ps)
Vc3dd c3vdd 0 {VDDV}
Vc3in c3in 0 PULSE(0 {VDDV} 1n 56.0000p 56.0000p 2n 4n)
Xc3 c3out c3in c3vdd vss sg13g2_buf_16
Cc3 c3out 0 26.28f
.measure tran Qc3 INTEG I(Vc3dd) FROM=0.9n TO=4.9n
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
* ---- c6: sg13g2_o21ai_1 arc A1->Y  CL=4.26fF  slew20-80=80.7ps (tr=134.5ps)
Vc6dd c6vdd 0 {VDDV}
Vc6in c6in 0 PULSE(0 {VDDV} 1n 134.5000p 134.5000p 2n 4n)
Xc6 c6out c6in nlo nhi c6vdd vss sg13g2_o21ai_1
Cc6 c6out 0 4.26f
.measure tran Qc6 INTEG I(Vc6dd) FROM=0.9n TO=4.9n
* ---- c7: sg13g2_a21oi_1 arc A1->Y  CL=4.99fF  slew20-80=81.4ps (tr=135.7ps)
Vc7dd c7vdd 0 {VDDV}
Vc7in c7in 0 PULSE(0 {VDDV} 1n 135.6667p 135.6667p 2n 4n)
Xc7 c7out c7in nhi nlo c7vdd vss sg13g2_a21oi_1
Cc7 c7out 0 4.99f
.measure tran Qc7 INTEG I(Vc7dd) FROM=0.9n TO=4.9n
* ---- c8: sg13g2_mux2_1 arc A0->X  CL=5.66fF  slew20-80=75.6ps (tr=126.0ps)
Vc8dd c8vdd 0 {VDDV}
Vc8in c8in 0 PULSE(0 {VDDV} 1n 126.0000p 126.0000p 2n 4n)
Xc8 c8out c8in nlo nlo c8vdd vss sg13g2_mux2_1
Cc8 c8out 0 5.66f
.measure tran Qc8 INTEG I(Vc8dd) FROM=0.9n TO=4.9n
* ---- c9: sg13g2_mux2_1 arc S->X  CL=5.66fF  slew20-80=75.6ps (tr=126.0ps)
Vc9dd c9vdd 0 {VDDV}
Vc9in c9in 0 PULSE(0 {VDDV} 1n 126.0000p 126.0000p 2n 4n)
Xc9 c9out nlo nhi c9in c9vdd vss sg13g2_mux2_1
Cc9 c9out 0 5.66f
.measure tran Qc9 INTEG I(Vc9dd) FROM=0.9n TO=4.9n
.tran 0.5p 5n
.options timeint reltol=1e-5 abstol=1e-13
.end
