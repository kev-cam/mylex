* th22_mc.sp — Muller C-element with per-device Vt mismatch (Monte-Carlo).
* Each transistor carries an independent DELVTO ~ AGAUSS(0, kvt*σ_Vt, 1), where
* σ_Vt = A_Vt/√(W·L) (Pelgrom; A_Vt≈3.5 mV·µm for SG13G2 130nm). Xyce .SAMPLING
* samples each AGAUSS per run; DELVTO reaches the PSP103 threshold LIVE through
* the PyMS callback (one .so, no per-sample rebuild). kvt scales overall spread.
* Ports: A B Y VDD VSS   (drop-in for th22)
.subckt th22 A B Y VDD VSS
.param kvt=1

* --- Pull-up stack: A,B series to X --- (pMOS W=0.7 L=0.13 -> σ=11.6mV)
MPA  N1 A VDD VDD sg13g2_pmos W=0.7u  L=0.13u DELVTO={AGAUSS(0,kvt*11.6m,1)}
MPB  X  B N1  VDD sg13g2_pmos W=0.7u  L=0.13u DELVTO={AGAUSS(0,kvt*11.6m,1)}
* --- Pull-down stack: A,B series to X --- (nMOS W=0.35 L=0.13 -> σ=16.4mV)
MNA  N2 A VSS VSS sg13g2_nmos W=0.35u L=0.13u DELVTO={AGAUSS(0,kvt*16.4m,1)}
MNB  X  B N2  VSS sg13g2_nmos W=0.35u L=0.13u DELVTO={AGAUSS(0,kvt*16.4m,1)}
* --- Output inverter X -> Y ---
MPY  Y  X VDD VDD sg13g2_pmos W=0.7u  L=0.13u DELVTO={AGAUSS(0,kvt*11.6m,1)}
MNY  Y  X VSS VSS sg13g2_nmos W=0.35u L=0.13u DELVTO={AGAUSS(0,kvt*16.4m,1)}
* --- Weak feedback keeper: Y -> inv -> X ---
MPK  X  Y VDD VDD sg13g2_pmos W=0.35u L=1.0u  DELVTO={AGAUSS(0,kvt*5.9m,1)}
MNK  X  Y VSS VSS sg13g2_nmos W=0.15u L=1.0u  DELVTO={AGAUSS(0,kvt*9.0m,1)}
.ends th22
