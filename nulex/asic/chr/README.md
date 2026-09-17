# nulex/asic/chr — SG13G2 TH-cell characterization

Timing (Liberty NLDM) for the native TH cells in the IHP SG13G2 domain, so the
async TH-gate netlists can be timed/placed in SG13G2 (not just the sky130
realization of `../../lib/th_pdk`).

    python3 characterize_th.py --from-lib <sg13g2_stdcell.lib> [out.lib]
    python3 characterize_th.py --spice [out.lib]        # transistor gold (needs PSP103)

## Two paths

**`--spice` — the gold, native-transistor path.** Xyce transient sweeps of the
transistor-level cells (`ldx/asic/cells/th22.sp`, `th_gates.sp`) with the SG13G2
PSP103 model card (`kestrel/sim/models/sg13g2_psp103_tt.lib`): input-slew × output-
load grid → propagation delay + output transition (+ the C-element set/reset/hold)
→ NLDM tables. This is the real characterization of the native C-element (its
feedback keeper, the loop/hold delay).

> **Blocked in this environment.** The stock `/usr/local/bin/Xyce` has **no PSP103
> device** — the model card loads but `sg13g2_nmos/pmos` don't bind. The ldx flow
> used a PyMS-built `psp103_sg13g2.so` plugin (or the custom `Xyce-8` build), which
> aren't installed here (nor is another PSP103-capable SPICE). The harness detects
> this and stops with that message. It runs unchanged once a PSP103-capable Xyce is
> available (rebuild the plugin via `share/xyce/PyMS`, or install the custom Xyce-8).

**`--from-lib` — SG13G2-domain timing available now.** Derives the TH-cell Liberty
from IHP's **silicon-characterized** `sg13g2_stdcell` library (real 1.2 V/25 °C
NLDM), realizing the comb TH cells on it (th22=and2, th12=or2, th13=or3, th33=and3,
th44=and4). Produces `th_cells_sg13g2.lib` — verified to `read_liberty` cleanly in
OpenROAD, so a TH netlist times/places in the SG13G2 domain today.

## Honest status

- Delivered now: SG13G2-domain NLDM timing for the **comb** TH cells (real IHP
  characterization, via the std-cell realization). The hysteretic C-element and
  weighted gates compose these (their timing is the path sum through the
  composition — see `../../lib/th_compose.v`).
- Not delivered here: the **native-transistor** timing of `th22.sp` (the standalone
  Sutherland C-element with its keeper), which is the `--spice` gold path — blocked
  only by the missing PSP103 device in this environment, not by the method. The
  harness is complete and waiting for a PSP103-capable simulator.
