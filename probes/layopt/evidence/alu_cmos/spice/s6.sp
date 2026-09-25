ALU dominant-cell energy per output toggle (SG13G2, PSP103)
.hdl "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
.include "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
.include "/usr/local/src/mylex/probes/layopt/evidence/alu_cmos/spice/shim_full.sp"
.include "/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/spice/sg13g2_stdcell.spice"
.param VDDV=1.2
VHI nhi 0 {VDDV}
VLO nlo 0 0
VSSG vss 0 0
* ---- c6: sg13g2_o21ai_1 arc A1->Y  CL=4.26fF  slew20-80=80.7ps (tr=134.5ps)
Vc6dd c6vdd 0 {VDDV}
Vc6in c6in 0 PULSE(0 {VDDV} 1n 134.5000p 134.5000p 2n 4n)
Xc6 c6out c6in nlo nhi c6vdd vss sg13g2_o21ai_1
Cc6 c6out 0 4.26f
.measure tran Qc6 INTEG I(Vc6dd) FROM=0.9n TO=4.9n
.measure tran VXc6 MAX V(c6out) FROM=0.9n TO=4.9n
.measure tran VNc6 MIN V(c6out) FROM=0.9n TO=4.9n
.tran 2p 5n
.options timeint reltol=1e-4 abstol=1e-12
.end
