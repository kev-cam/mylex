# nulex/asic/chr/mc — Monte-Carlo reliability of the native async cells

Model-native Monte-Carlo of the SG13G2 transistor-level threshold cells under
**per-device local Vt mismatch**, to quantify how reliable the RTL→NCL→cell
methodology is before scaling up. First target: the **th22 Muller C-element**
(the stateful, keeper-latched heart of the DIMS dual-rail logic).

## How the variability is injected (the model-native way)

Each transistor carries an independent threshold shift
`DELVTO ~ AGAUSS(0, kvt·σ_Vt, 1)`, where `σ_Vt = A_Vt/√(W·L)` (Pelgrom;
`A_Vt ≈ 3.5 mV·µm` for 130 nm). `DELVTO` is a *native PSP103 instance
parameter* (`VFB_T = VFB_i + STVFB_i·ΔT + DELVTO_i`), so this is real
model-native mismatch — not an external offset hack.

The PyMS GiNaC device path normally **bakes** every parameter as a compile-time
constant, which would freeze `DELVTO` at build time and make `.SAMPLING`
inert. So PyMS grew a **runtime-callback param** path (see the xyce tree,
`utils/PyMS/vae/`): a param named in `PYMS_CALLBACK_PARAMS` is kept *symbolic*
in the generated `.so` and fetched per-eval through a shell callback
`_pcb("DELVTO")` instead of a literal. A compiler cannot const-fold an opaque
call, so the value stays live — Xyce `.SAMPLING`/AGAUSS reaches it through a
**single `.so` per geometry** (no per-sample rebuild), and the shell returns the
value for whichever device instance is currently being evaluated (true
per-device local mismatch). Verified: with `.STEP DELVTO`, the Id–Vg curve
translates by exactly the DELVTO amount (rigid Vt shift), one `.so` shared.

## Run

    XYCE=/usr/local/src/xyce-build/src/Xyce PYMS_DIR=/usr/local/share/xyce/PyMS \
      ./run_sweep.sh 1 2 3 4          # kvt = 1,2,3,4 ; N=200 each

`run_sweep.sh` forces `PYMS_CALLBACK_PARAMS=DELVTO`, runs Xyce `.SAMPLING`
(Monte Carlo) at each mismatch scale `kvt`, and calls `analyze_mc.py` for
functional yield + propagation-delay statistics from the per-sample `.mt`
files.

## Result (N=200 per level, SEED=1)

Static levels are rail-to-rail robust (all highs = 1.2 V ± 1e-7, all lows
≤ 1.6 µV) — a keeper-latched cell's DC levels are insensitive to Vt mismatch;
the mismatch shows up in **timing**:

| Mismatch          | Functional | Set delay tset1 | Reset delay trst | (delay σ) |
|-------------------|-----------:|----------------:|-----------------:|-----------|
| 1× (σ≈6–16 mV/dev)|  200 / 200 |  356 ± 12 ps     |  440 ± 15 ps     | nominal   |
| 2×                |  200 / 200 |  358 ± 24 ps     |  442 ± 31 ps     | ~2×       |
| 3×                |  200 / 200 |  361 ± 38 ps     |  446 ± 48 ps     | ~3×       |
| 4× (σ≈24–66 mV)   |  200 / 200 |  366 ± 54 ps     |  452 ± 67 ps     | ~4×       |

**Findings**

1. **0 functional failures in 800 samples**, even at 4× nominal (≈4σ-equivalent)
   local Vt mismatch. The C-element tolerates realistic — and unrealistic —
   process variation.
2. Delay **σ scales linearly** with mismatch magnitude; the **mean barely
   shifts** (zero-mean per-device Vt adds spread, not bias).
3. **Reset (440 ps) is slower than set (357 ps)** — the keeper-fight signature,
   consistent with the NLDM characterization (`../README.md`: reset/fall slower
   than set/rise for the native C-element).

## Files

- `th22_mc.sp` — th22 with per-device `DELVTO=AGAUSS(0,kvt·σ,1)` (drop-in for
  `ldx/asic/cells/th22.sp`); per-device σ pre-computed from W·L.
- `mc_th22.cir` — parameterized Xyce deck (6-phase set/hold/reset sequence,
  level + delay measures, `.SAMPLING` MC block).
- `run_sweep.sh` — kvt sweep driver.
- `analyze_mc.py` — functional yield + delay stats from the `.mt` files.
- `out/` — generated per-run decks, logs, `.mt` files (not committed).
