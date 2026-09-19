* th_cells_sg13g2.sp — nulex supplement to ldx/asic/cells for the phys binding.
* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
*
* The transistor-level TH cells map_ncl_struct.py --target spice instantiates,
* that ldx/asic/cells/{th22.sp,th_gates.sp} does not yet define. Same SG13G2
* convention: sg13g2_nmos/pmos (PSP103, level=103) included by the caller;
* NMOS W=0.35u, PMOS W=0.7u, L=0.13u minimum; series stacks widened.
*
* th1n (1-of-n threshold = OR-n) are DEGENERATE threshold gates: no hysteresis
* is possible (a single input crossing must switch the output), so they are
* plain static CMOS NOR-n + output inverter — exactly the th12 form in
* th_gates.sp, extended to 3 and 4 inputs. They are the DIMS rail collectors
* (map_ncl_struct COLLECT: fan-in 2->th12, 3->th13, 4->th14).

*==============================================================================
* TH13 — 1-of-3 threshold (OR3). NOR3 + inverter.
*==============================================================================
.subckt th13 A B C Y VDD VSS
* Pull-up: 3 PMOS in series (X high only when A=B=C=0); widened for the stack.
MPA  N1 A VDD VDD sg13g2_pmos W=1.0u L=0.13u
MPB  N2 B N1  VDD sg13g2_pmos W=1.0u L=0.13u
MPC  X  C N2  VDD sg13g2_pmos W=1.0u L=0.13u
* Pull-down: 3 NMOS in parallel (any input high pulls X low).
MNA  X  A VSS VSS sg13g2_nmos W=0.35u L=0.13u
MNB  X  B VSS VSS sg13g2_nmos W=0.35u L=0.13u
MNC  X  C VSS VSS sg13g2_nmos W=0.35u L=0.13u
* Output inverter X -> Y.
MPY  Y  X VDD VDD sg13g2_pmos W=0.7u  L=0.13u
MNY  Y  X VSS VSS sg13g2_nmos W=0.35u L=0.13u
.ends th13

*==============================================================================
* TH14 — 1-of-4 threshold (OR4). NOR4 + inverter.
*==============================================================================
.subckt th14 A B C D Y VDD VSS
* Pull-up: 4 PMOS in series (X high only when all inputs 0); widened further.
MPA  N1 A VDD VDD sg13g2_pmos W=1.4u L=0.13u
MPB  N2 B N1  VDD sg13g2_pmos W=1.4u L=0.13u
MPC  N3 C N2  VDD sg13g2_pmos W=1.4u L=0.13u
MPD  X  D N3  VDD sg13g2_pmos W=1.4u L=0.13u
* Pull-down: 4 NMOS in parallel.
MNA  X  A VSS VSS sg13g2_nmos W=0.35u L=0.13u
MNB  X  B VSS VSS sg13g2_nmos W=0.35u L=0.13u
MNC  X  C VSS VSS sg13g2_nmos W=0.35u L=0.13u
MND  X  D VSS VSS sg13g2_nmos W=0.35u L=0.13u
* Output inverter X -> Y.
MPY  Y  X VDD VDD sg13g2_pmos W=0.7u  L=0.13u
MNY  Y  X VSS VSS sg13g2_nmos W=0.35u L=0.13u
.ends th14
