* nclfa4_mc.sp — Monte-Carlo wrapper of the 4-bit NCL ripple-carry adder.
* Same topology as ldx/asic/cells/nclfa4.sp, but threads the mismatch scale kvt
* DOWN to each nclfa instance (which threads it to its th23/th34w2 gates), so a
* top-level .SAMPLING of kvt actually scales the per-device DELVTO. Each of the
* 4x4 = 16 gate instances draws independent AGAUSS per device -> 240 independent
* per-device DELVTO. Requires nclfa_mc.sp + th23_mc.sp + th34w2_mc.sp (included
* by the caller). Carry ripples ci -> c1 -> c2 -> c3 -> coH (worst-case path).
.subckt nclfa4
+ a0H a0L a1H a1L a2H a2L a3H a3L
+ b0H b0L b1H b1L b2H b2L b3H b3L
+ ciH ciL
+ s0H s0L s1H s1L s2H s2L s3H s3L
+ coH coL
+ VDD VSS
.param kvt=1
Xfa0 a0H a0L b0H b0L ciH ciL s0H s0L c1H c1L VDD VSS nclfa kvt={kvt}
Xfa1 a1H a1L b1H b1L c1H c1L s1H s1L c2H c2L VDD VSS nclfa kvt={kvt}
Xfa2 a2H a2L b2H b2L c2H c2L s2H s2L c3H c3L VDD VSS nclfa kvt={kvt}
Xfa3 a3H a3L b3H b3L c3H c3L s3H s3L coH coL VDD VSS nclfa kvt={kvt}
.ends nclfa4
