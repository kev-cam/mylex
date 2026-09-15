# nulex/setup — layout toolchain bring-up

The physical-implementation side of nulex (ASYNC-PLAN §8/§10, LAYOUT-OPT.md L3/L5).
nulex emits isochronic-fork constraints (`../formal/constraints.py`); layopt places
and balances them in sky130 geometry. This directory reproduces the toolchain.

## Two scripts, by privilege

| script | sudo? | does |
|---|---|---|
| `install_pdk.sh` | no | sky130 PDK via volare venv; wires layopt's LIB dir (`~/tools/sky130_fd_sc_hd`: tlef + merged LEF + per-cell GDS split) |
| `install_layout_root.sh` | **yes** | OpenROAD clone + `DependencyInstaller.sh` (apt) + optional KLayout. Does *not* build. |

Run order: `bash install_pdk.sh` (user)  →  `sudo bash install_layout_root.sh` (root)
→  `~/tools/OpenROAD/etc/Build.sh` (user, ~30-60 min).

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
