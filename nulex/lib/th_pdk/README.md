# th_pdk — physical (LEF/Liberty/GDS) views for the TH cells

The last piece joining the async TH-gate netlists (map_ncl_struct) to the physical
flow: so a structural threshold-gate design can go through OpenROAD P&R and layopt.

    python3 gen_th_pdk.py .    # -> th_cells.lef, th_cells.lib, <th>.gds

Real custom TH-cell transistor layout is out of scope. Instead each **combinational**
TH cell is realized on its sky130_fd_sc_hd equivalent, and its physical views are
derived from that cell by renaming the macro + signal pins (A,B,C,D->a,b,c,d ; X->y),
keeping the power pins and geometry — same site (`unithd`) and rails, so TH cells
place-and-route alongside sky130 fillers/taps.

| TH cell | function | sky130 cell |
|---|---|---|
| th22 | a·b (2-of-2) | and2_1 |
| th12 | a+b (1-of-2) | or2_1 |
| th13 | a+b+c (1-of-3) | or3_1 |
| th14 | a+b+c+d (1-of-4) | or4_1 |
| th33 | a·b·c (3-of-3) | and3_1 |
| th23 | majority(a,b,c) (2-of-3) | maj3_1 |
| th44 | a·b·c·d (4-of-4) | and4_1 |

Demonstrated (`../../mapper/struct/run_th_pnr.sh`): the `add4` structural TH netlist
(68×th22 + 14×th12 + 10×th13) through OpenROAD floorplan/place/route on these views
— **0 DRC**, 594 µm² — then layopt `def2flat` + `extract` reads the routed design
(11964 shapes, 352 nets), the same extraction that feeds `objective.fork_balance`.

## Limits (honest)

- These are the **comb** TH cells (the DIMS datapath). The hysteretic `qdi` C-elements
  and the weighted/threshold gates (th24/th34/th34w2/th23w2, used only by the Fant
  adder) are not single sky130 cells — they need a composed cell (a Muller C-element
  is a feedback AOI) and are future work.
- Realized-on-sky130, not native TH silicon: the "layout" is a real sky130 cell's
  layout, characterized timing and all — sound for P&R/extraction, but the QDI timing
  assumptions of a true TH cell (hysteresis) aren't in the comb sky130 mapping.
