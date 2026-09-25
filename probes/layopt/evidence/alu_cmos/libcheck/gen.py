#!/usr/bin/env python3
"""One-cell OpenSTA power evaluation at the SAME load / input slew / arc as the
SPICE decks, so the transistor-vs-liberty ratio isolates the MODEL difference
(not a load, slew or arc mismatch)."""
CELLS=[
 ("sg13g2_inv_1",   "Y","A", [],                    9.34, 64.9),
 ("sg13g2_buf_1",   "X","A", [],                   21.68, 72.2),
 ("sg13g2_buf_8",   "X","A", [],                   32.87, 78.9),
 ("sg13g2_buf_16",  "X","A", [],                   26.28, 33.6),
 ("sg13g2_nand2_1", "Y","A", [("B",1)],             4.93, 86.2),
 ("sg13g2_nor2_1",  "Y","A", [("B",0)],             4.75, 87.0),
 ("sg13g2_o21ai_1", "Y","A1",[("A2",0),("B1",1)],   4.26, 80.7),
 ("sg13g2_a21oi_1", "Y","A1",[("A2",1),("B1",0)],   4.99, 81.4),
 ("sg13g2_mux2_1",  "X","A0",[("A1",0),("S",0)],    5.66, 75.6),
 ("sg13g2_mux2_1",  "X","S", [("A0",0),("A1",1)],   5.66, 75.6),
]
T=4.75          # ns
ACT=1.0         # one output toggle per cycle -> E_tog = P*T/ACT
import os
vl=[]; tcl=[]
LIB="/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
for i,(cell,out,drv,side,cl,slew) in enumerate(CELLS):
    top=f"t{i}"
    ports=[drv]+[s for s,_ in side]
    vl.append(f"module {top}({', '.join(ports)}, o);")
    vl.append(f"  input {', '.join(ports)}; output o;")
    conn=[f".{out}(o)", f".{drv}({drv})"]+[f".{s}({s})" for s,_ in side]
    vl.append(f"  {cell} u0 ({', '.join(conn)});")
    vl.append("endmodule")
    t=[f"read_liberty {LIB}", f"read_verilog cells.v", f"link_design {top}",
       f"create_clock -name vclk -period {T}",
       f"set_load {cl/1000.0} [get_nets o]",
       f"set_input_transition {slew/1000.0} [all_inputs]",
       f"set_power_activity -input_port {drv} -activity {ACT} -duty 0.5"]
    for s,lev in side:
        t.append(f"set_power_activity -input_port {s} -activity 0.0 -duty {float(lev)}")
    t.append(f'puts "@@@CELL {cell} arc={drv}->{out} CL={cl} slew={slew}"')
    t.append("report_power -digits 9")
    t.append("report_power -instances [get_cells u0] -digits 9")
    tcl.append('\n'.join(t))
open('cells.v','w').write('\n'.join(vl)+'\n')
for i,t in enumerate(tcl): open(f'c{i}.tcl','w').write(t+'\n')
print("wrote", len(CELLS), "cells")
