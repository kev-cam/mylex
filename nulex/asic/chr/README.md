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

> **PSP103 UNBLOCKED (2026-09-19), but a transient ceiling remains.** The PyMS
> GiNaC device path now binds SG13G2 PSP103 via `.hdl` JIT — run with
> `XYCE=/usr/local/src/xyce-build/src/Xyce` + `PYMS_DIR=/usr/local/share/xyce/PyMS`
> (the fixed build). DC is solid (Id-Vg/Id-Vd, and the native C-element's DC
> set/reset transfer characterize cleanly), and the light-load transient gives real
> timing (th22 set ~0.30–0.43 ns @1f). **However** the JIT PSP103 stiff transient
> DIVERGES above ~1f load ("time step too small"), so the full (slew × load) NLDM
> sweep is not yet reliable — the ceiling is now the PSP103 **transient charge-model
> robustness** (its accuracy-first emit leaves non-smooth charge derivatives), not a
> missing device. The delivered increment is the phys binding + per-cell DC logic
> (`../../mapper/struct/run_phys.sh`); full gold NLDM awaits that fix, and
> `--from-lib` gives P&R-usable comb timing meanwhile.

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
- Native-transistor `--spice` gold path: PSP103 now **binds** (PyMS-fixed Xyce), so
  the C-element's DC set/reset transfer and its light-load transient timing
  characterize (real: th22 set ~0.30–0.43 ns @1f). The full (slew × load) NLDM
  sweep is still **not delivered** — the JIT PSP103 stiff transient diverges above
  ~1f load; the remaining gate is PSP103 transient charge-model robustness, not the
  device or the method. The phys binding + per-cell DC logic are proven now
  (`../../mapper/struct/run_phys.sh`).
