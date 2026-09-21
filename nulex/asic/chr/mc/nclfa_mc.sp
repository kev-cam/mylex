* nclfa_mc.sp — Monte-Carlo wrapper of the NCL full adder (Fant canonical form).
* Identical topology to ldx/asic/cells/nclfa.sp, but threads the mismatch scale
* `kvt` DOWN to each TH-gate instance so a top-level .STEP/.SAMPLING of kvt
* actually scales the per-device DELVTO. (The plain nclfa.sp does NOT pass kvt,
* so the th23_mc/th34w2_mc subckt-local `.param kvt=1` would shadow it and pin
* every run at nominal mismatch.) Each of the 4 gate instances still draws its
* own independent AGAUSS per device -> 60 independent per-device DELVTO.
* Requires th23_mc.sp and th34w2_mc.sp (included by the caller).
.subckt nclfa aH aL bH bL ciH ciL sH sL coH coL VDD VSS
.param kvt=1
Xco_h  aH bH ciH coH VDD VSS th23   kvt={kvt}
Xco_l  aL bL ciL coL VDD VSS th23   kvt={kvt}
Xs_h   coL aH bH ciH sH  VDD VSS th34w2 kvt={kvt}
Xs_l   coH aL bL ciL sL  VDD VSS th34w2 kvt={kvt}
.ends nclfa
