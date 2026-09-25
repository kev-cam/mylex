ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c8: sg13g2_mux2_1 arc A0->X  CL=5.66fF  slew20-80=75.6ps (tr=126.0ps)
Vc8dd c8vdd 0 {VDDV}
Vc8in c8in 0 PULSE(0 {VDDV} 1n 126.0000p 126.0000p 2n 4n)
Xc8 c8out c8in nlo nlo c8vdd vss sg13g2_mux2_1
Cc8 c8out 0 5.66f
.measure tran Qc8 INTEG I(Vc8dd) FROM=0.9n TO=4.9n
.measure tran VXc8 MAX V(c8out) FROM=0.9n TO=4.9n
.measure tran VNc8 MIN V(c8out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
