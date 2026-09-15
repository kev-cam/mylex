# nulex/setup — layout toolchain bring-up

The physical-implementation side of nulex (ASYNC-PLAN §8/§10, LAYOUT-OPT.md L3/L5).
nulex emits isochronic-fork constraints (`../formal/constraints.py`); layopt places
and balances them in sky130 geometry. This directory reproduces the toolchain.

## Three scripts, by privilege

| script | sudo? | does |
|---|---|---|
| `install_pdk.sh` | no | sky130 PDK via volare venv; wires layopt's LIB dir (`~/tools/sky130_fd_sc_hd`: tlef + merged LEF + per-cell GDS split) |
| `install_layout_root.sh` | **yes** | OpenROAD clone + `DependencyInstaller.sh -base` (apt only) + optional KLayout. Does *not* build, does *not* touch cmake. |
| `build_openroad.sh` | no | `DependencyInstaller.sh -common -local` (real cmake + from-source deps → `~/.local`) then `Build.sh -local` (~30–60 min). |

Run order: `bash install_pdk.sh` (user) → `sudo bash install_layout_root.sh` (root)
→ `bash build_openroad.sh` (user).

## Two gotchas this box hit (why the split, not a bare `-all`)

1. **`DependencyInstaller.sh` with no flag errors out** — it demands one of
   `-all|-base|-common|-bazel|-bazel-dev` (`error "You must use one of: ..."`).
   That was the first failure. Always pass a flag.
2. **The smak `cmake` shim must not be clobbered.** `/usr/local/bin/cmake` is a
   symlink to smak's driver (reports 3.31.4); OpenROAD wants 3.31.9. A root
   `-all`/`-common` would install cmake with `--prefix=/usr/local`, overwriting
   that symlink, and route every dep's cmake through smak's interpreter. So root
   runs only `-base` (apt, no cmake), and the common deps + build run non-root
   with `-local` → everything in `~/.local`, whose `bin` precedes `/usr/local/bin`
   in PATH, so a real cmake shadows the shim and the shim is left intact.
3. **OpenROAD's default build system is now Bazel** (hermetic, needs `bazelisk`
   and re-fetches its own toolchain, ignoring the `~/.local` deps). `build_openroad.sh`
   passes `Build.sh -cmake-build`, which uses the classic CMake build that consumes
   exactly the deps `-common` installed (its pre-compile check wants
   cmake/bison/flex/swig/gcc/g++, all present in `~/.local/bin`).

## Result (validated 2026-09-15)

OpenROAD `26Q3-2260-ge2787ffca2` built + installed to `~/.local/bin/openroad`
(on PATH). Smoke test: reads the sky130 tech + cell LEF, 14 layers, 1000 dbu/µm,
**all 437 std-cell masters** load and resolve by name. KLayout 0.30.0 present.
Full stack — sky130 PDK, Xyce, KLayout, OpenROAD — installed and validated.

## What's needed vs optional

- **sky130 PDK** — required; layopt's LEF/GDS target. Installed + wired + validated.
- **Xyce** — present (`/usr/local/bin/Xyce`); L5 corner sim. layopt emits the deck.
- **OpenROAD** — full-design P&R (maps fork endpoints to physical shapes at scale).
- **KLayout** — optional signoff DRC/extraction oracle; layopt has its own extractor.

## Validation (no OpenROAD needed)

The fork-balance consumer of nulex's constraint set runs green on the installed PDK:

    cd ../../probes/layopt && LAYOUT_SCRATCH=/tmp/lo python3 l3_fork_balance.py --iters 40
    # li1 branch fork: spread 74.90 ps -> 17.00 ps ; met2: 0.96 ps -> 0.10 ps

i.e. constraints.py (net -> driver pin + receiver pins) -> objective.fork_balance
-> branch resize minimising Elmore-delay spread, in real sky130 RC.
