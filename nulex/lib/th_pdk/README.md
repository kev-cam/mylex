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

## Composed cells (not a single sky130 gate)

The hysteretic C-elements and weighted/threshold gates are **composed** from the leaf
cells above — see `../th_compose.vhd` (behavioral, verified vs spec in `tb_compose`)
and `../th_compose.v` (sky130-cell netlists for P&R):

- **Hysteretic C-element** (`th22/33/44` `composed`): `y = set(inputs) | (y & any(inputs))`
  with the feedback net as the state. For 2-in this is the Muller C-element = `maj3(a,b,y)`.
- **Weighted / threshold** (`th23w2/th34w2/th24/th34`): Boolean compositions of and/or.

Verified: `run_struct.sh` step 7 checks all four weighted cells exhaustively and the
three C-elements against the hysteretic (`qdi`) reference; `run_th_pnr.sh` step 5 routes
a design of four Muller C-elements (`maj3` + feedback) + a weighted cell through OpenROAD
— **0 DRC** — so the feedback loops route cleanly.

## Limits (honest)

- Realized-on-sky130, not native TH silicon: the "layout" is a real sky130 cell's
  layout, characterized timing and all — sound for P&R/extraction, but the QDI timing
  assumptions of a true TH cell aren't in the sky130 mapping (a real C-element would be
  one characterized cell, not a `maj3` + a feedback wire whose delay must be bounded).
