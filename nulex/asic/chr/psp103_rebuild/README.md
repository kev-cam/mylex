# PSP103 / BSIM-CMG Xyce device path via PyMS (GiNaC) — WORKING

The gold `--spice` path of `../characterize_th.py` needs a Xyce with the SG13G2
transistor models (PSP103 for the PDK, BSIM-CMG for cross-checks). This directory
is the PyMS (GiNaC) device path that provides them. It is the transistor-level
foundation for `bfit` (sv2ghdl/bfit/bfit.py), which turns those device sims into
behavioral models for the NCL / async cells.

**Status: works end-to-end in Xyce, no manual `.so`.** PSP103 SG13G2 Id-Vg,
Id-Vd, and a rail-to-rail CMOS inverter VTC all run correctly; BSIM-CMG (108)
Id-Vd is a correct, monotonic family across the full Vg/Vd sweep. Everything is
driven by a JIT per-instance math build — the generated device shell bakes this
instance's parameters and compiles the GiNaC `vae_eval` `.so` on first use.

The old "RTTI/plugin-ABI wall" in earlier notes was a **stale install**
(guard-fixed `libXyceLib` rebuilt but not deployed), not an ABI problem. Testing
is against `/usr/local/src/xyce-build/src/Xyce` with
`LD_LIBRARY_PATH=/usr/local/src/xyce-build/src`; `/usr/local/bin/Xyce` is still
the pre-guard lib (`deploy_xyce_fix.sh` deploys the fix — needs sudo, separate
from these PyMS patches).

## Contents

Re-deployable full copies (install to `/usr/local/share/xyce/PyMS/vae/`):

- `ginac_emitter.py` — the GiNaC emitter (hot path). Emits a metaprogram that
  compiles+runs to print the specialized `vae_eval`. Handles voltage-dependent
  conditionals / min / max / ternary via **indicator-selects** (value from a
  short-circuit C++ ternary, arithmetic form `base+(alt-base)*S` for forward-mode
  AD), contribution gating, guard-lowering, and `$param_given()`.
- `xyce_device_gen.py` — the device-shell generator: internal-node collapse
  (`V(a,b)<+0`), JIT per-instance build in `processParams()`, `TYPE`-from-keyword
  (nmos=+1 / pmos=-1, case-insensitive on the UPPERCASE `getType()`), and the
  `__GIVEN__` marker (see the param_given fix).
- `build_vae_so.py` — the JIT math builder invoked by the shell: `parse_file` →
  `emit_ginac_program(params, given_params)` → `g++ -lginac -lcln` → run → wrap
  (`VaeState` ABI) → `g++ -shared`. Retries dropping zero-valued params.

Patches (diffs vs the pristine xyce-tree source, applied on top of each other):

- `ginac_emitter_selects.patch` — indicator-selects + contribution gating +
  guard-lowering + jacobian `_san` + `hypsmooth/hypmax/Tempdep` + reserved-name
  mangling + `_safe_ex` + `ddx` stub.
- `xyce_device_gen_jit.patch` — node-collapse + JIT-build `processParams` + TYPE.
- `param_given_fix.patch` — **this session's fix** (see below).

Support: `repro_tool.py` + `repro_models/*.va` (10 micro-models proving each
emitter mechanism), `deploy_xyce_fix.sh` (crash-fix deploy — needs sudo).
Deprecated (kept for history): `codegen_pyms.patch`, `build_eval.py`,
`build_vae_ginac.py`, `pyms_plugin_register.C` (the sympy `codegen.py` / `-plugin`
route, superseded by the GiNaC + auto-load path).

## The param_given fix (BSIM-CMG low-Vg sign inversion)

**Symptom:** BSIM-CMG Id-Vd at low Vg was sign-inverted and huge (Vg=0.25 gave
`+5.86e-4` while Vg≥0.5 were correctly negative).

**Root cause:** `$param_given()` over-reporting. The JIT shell serializes ALL
params (user-given *and* defaulted) into the params file, and the emitter used
`param_values.keys()` as the `$param_given` set — so defaulted params read as
user-given. That made

    if (!$param_given(NVTM))  nVtm = Vtm*ThetaSS*(1 + (CIT+cdsc)/T1);
    else                      nVtm = NVTM;     // NVTM defaults to 0

take the `else` → `nVtm = 0`. With `nVtm = 0`, `T14 = 2*nVtm = 0`, and every
`/nVtm` term hit GiNaC `pole_error` → swallowed to `0` by the `_safe_ex` guard →
the surface-potential Newton solve froze (`F0 = -F1`, `phis` = const) → the
inversion charge `qis = vgsfbeff - phis - vpolys` went negative in subthreshold.
The same bug zeroed `Theta_SCE`/`Theta_SW`/`Theta_DIBL` — the whole
SCE/DIBL/subthreshold-swing physics (all `!$param_given`-guarded).

**Fix (3 coordinated edits):**

1. `xyce_device_gen.py` — the shell emits a `__GIVEN__=name,...` line built from
   Xyce's real `given()` / `model_.given()` (part of the cache-key hash).
2. `build_vae_so.py` — parses `__GIVEN__` into a set, passes `given_params=` to
   `emit_ginac_program`.
3. `ginac_emitter.py` — a `given_params` kwarg on `GiNaCEmitter` /
   `emit_ginac_program` drives `$param_given()`; falls back to
   `param_values.keys()` only when unset (legacy callers unaffected).

PSP103 uses `$param_given` zero times, so it is provably unaffected — verified.

## Install + reproduce

    # 1. install the three files (back up first)
    cp ginac_emitter.py xyce_device_gen.py build_vae_so.py \
       /usr/local/share/xyce/PyMS/vae/
    # 2. clear the shell + math caches (mtime freshness ignores the generator)
    rm -rf /tmp/pyms_hdl_cache /tmp/pyms_vae_cache
    # 3. run (guard-fixed lib; PYMS_DIR forces the installed copies)
    export LD_LIBRARY_PATH=/usr/local/src/xyce-build/src
    export PYMS_DIR=/usr/local/share/xyce/PyMS XYCE_BUILD=/usr/local/src/xyce-build
    /usr/local/src/xyce-build/src/Xyce psp_idvg.cir   # or bidvd.cir / inv.cir

First sim per unique geometry takes ~2-3 min (GiNaC metaprogram compile); the
`.so` is then cached by (va, params) hash.

## Verified (2026-09-18, installed path, vs xyce-build)

- **BSIM-CMG Id-Vd** — `I(Vd)` negative + monotonic in Vd and Vg
  (Vg 0.25/0.5/0.75/1.0 @Vd=0.5 = -3.98e-6 / -1.37e-4 / -3.16e-4 / -4.90e-4).
- **PSP103 SG13G2** — Id-Vg monotonic 0 → -70µA; CMOS inverter VTC rail-to-rail
  1.2 → 0 V.
- **nulex** `run_struct.sh` — STRUCTURAL FLOW GREEN, no collateral.
- repro battery 10/10.

## Known limits

- AMS-suite decks use the cadence2xyce-inlined VA (pre-existing `qinv` parse
  issue) — use the raw `*_main.va` / `psp103.va` instead.
- Param-registration completeness — a few card params (e.g. `VASATCV`) are "not
  found" → default; a CV param, no effect on DC.
