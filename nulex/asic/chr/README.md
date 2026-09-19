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

> **PSP103 UNBLOCKED + transient ceiling RESOLVED (2026-09-19).** The PyMS GiNaC
> device path binds SG13G2 PSP103 via `.hdl` JIT — run with
> `XYCE=/usr/local/src/xyce-build/src/Xyce` + `PYMS_DIR=/usr/local/share/xyce/PyMS`.
> The earlier stiff-transient divergence above ~1f load was the **analytic jacobian
> being inconsistent with the eval** (forward-AD of the indicator-select arithmetic
> form diverged from the ternary value path — charge derivatives came out wrong
> magnitude AND sign at narrow-W+long-L geometries; DC tolerates it, transient
> doesn't). FIXED in `build_vae_so.py` by computing `vae_jacobian` via FINITE
> DIFFERENCE of the eval (consistent with F/Q by construction). RESULT: the native
> C-element characterizes over the FULL (slew × load) grid — th22 set delay 0.30 ns
> (fast/light) → 0.74 ns (slow/heavy), transition 0.11 → 0.48 ns, **25/25 grid
> points, 0 divergence** (was mostly FAILED). DC Id-Vg is byte-identical to pre-fix
> (F/Q unchanged; only the jacobian). The gold `--spice` NLDM sweep is now reliable;
> `--from-lib` remains the quick comb-timing path.

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
- Native-transistor `--spice` gold path: PSP103 **binds** (PyMS-fixed Xyce) AND the
  stiff-transient divergence is **fixed** (FD jacobian in `build_vae_so.py`). The
  C-element now characterizes over the full (slew × load) grid — th22 set delay
  0.30→0.74 ns, transition 0.11→0.48 ns, 25/25 grid points, 0 divergence. The gold
  NLDM sweep is reliable; wiring the full multi-cell NLDM assembly into
  `characterize_th.py --spice` is the remaining build step (the physics/convergence
  is no longer the blocker).
