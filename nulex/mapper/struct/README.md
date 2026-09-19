# nulex structural TH-cell flow (map_ncl_struct)

The async counterpart to `../` (map_ncl.py): instead of instantiating the
behavioral `lib/ncl_gates` entities (whose threshold gates are FUNCTION calls
that vanish on synthesis), `map_ncl_struct.py` expands each primitive's DIMS
template into explicit **TH-cell instances** (`../../lib/th_cells.vhd`), so the
threshold gates survive as first-class cells — for physical lowering and for
isochronic-fork extraction.

    ./run_struct.sh          # 4-bit adder, end-to-end, exit 0 == green

## Multiple versions (ASYNC-PLAN binding layer)

`map_ncl_struct.py <json> <top> <out> --target T [--bind B]`:

| target | bind | use |
|---|---|---|
| `verilog` | — | self-contained blackbox-TH Verilog; `yosys read_verilog; flatten; write_json` → `constraints.py` fork extraction (TH cells stay opaque) |
| `vhdl` | `comb` | nvc-simulatable; stateless Boolean TH cells — functional / equivalence |
| `vhdl` | `qdi`  | nvc-simulatable; hysteretic C-element TH cells — true delay-insensitive |
| `spice` | — | **PHYS BINDING**: transistor-level SG13G2 `.subckt` — real TH-cell subckts + PSP103, for LVS / extraction / SPICE in the SG13G2 domain |

`th_cells.vhd` carries the `comb`/`qdi` architectures. The **`phys` binding is
`--target spice`** (`run_phys.sh`): each TH cell becomes its real transistor
subckt (`ldx/asic/cells/th22.sp` + `th_gates.sp`, plus `../../lib/th_cells_sg13g2.sp`
for the th13/th14 collectors), dual-rail nets are node pairs `n<bit>_L`/`_H`, and
the design is emitted as a `.subckt <top> <rail-nodes> VDD VSS` — the async block
lowered to silicon. Combinational only so far (sequential cells rejected; use
`--target vhdl` for registers). Verified by `run_phys.sh`: the emit's TH-cell
census matches the behaviorally-verified `--target verilog` netlist (whose logic
`run_struct.sh` proved == sync golden), and each transistor TH cell computes its
threshold function at DC (th22 C-element set/reset; th12/th13/th14 OR collectors),
using the PyMS-fixed PSP103-capable Xyce.

★ Block-level TRANSIENT of a mapped block is **not yet** a gate: the JIT PSP103
model converges in DC but its stiff transient diverges above ~1f load, so a full
NULL→DATA block transient and a full NLDM characterization (`asic/chr`, the gold
`--spice` path) await a more transient-robust PSP103 charge model. The binding and
per-cell DC logic are the delivered increment; the transistor timing of the native
C-element is unblocked at the light-load corner (real: ~0.30–0.43 ns set delay).

Registers: `--reg sync` (default) emits the sync-emulation `ncl_dff`; `--reg qdi`
emits a **multi-stage QDI pipeline**. Registers are assigned 4-phase STAGES by
their register-to-register dependency depth (`pipeline_stages`); each stage is a
bank of TH22 C-element latches (`../../lib/ncl_reg.vhd`) gated by that stage's
request, with completion `ko_s` = a C-element chain over the stage's is-DATA bits.
The handshake is wired **`ki_s = NOT(ko_{s+1})`** (a stage captures the opposite
phase of what its successor holds); the output stage's request is the external
`ki_in`, and `ko_out`/`ko_in` expose the output/input completions. No clock — a
self-timed pipeline. This makes the per-stage request-distribution and
completion-tree forks extractable (they don't exist with the clocked `ncl_dff`).
Register feedback (a cyclic dependency) is rejected by `qdi` — use `--reg desync`.

`--reg desync` handles **cyclic/feedback** logic (accumulators, counters, FSMs) that
pure QDI 4-phase can't (a self-loop can't return-to-NULL without losing its state).
It's the **desynchronization / bundled-data** binding (`../../lib/ncl_reg_desync.vhd`):
a stateless (comb) datapath that returns to NULL, and a register captured by a LOCAL
self-timed clock = completion detection through a MATCHED DELAY (so the next-state has
settled before capture; raw completion can pulse on a transient-complete value while a
stateless net settles). One capture per DATA token; the post-capture feedback recompute
is not re-latched. Registers share one bank/local-clock (VHDL target).

## What run_struct.sh proves (on `add4`, a=b=4 bit → 5-bit sum)

1. **Fork extraction:** 17 gates → 68×th22 + 14×th12 + 10×th13 (DIMS survives
   `yosys flatten`); `constraints.py` enumerates **40 dual-rail isochronic forks**
   (a_L[i]/a_H[i]/b_L[i]/b_H[i] each fork), via its JSON-submodule-ports source —
   no LEF. Path set feeds layopt's `objective.fork_balance` exactly as the sync
   flow does.
2. **Functional:** the TH netlist (comb) decodes to `a+b` for all 256 inputs.
3. **Both VHDL bindings** analyze + elaborate in nvc.
4. **Structural QDI register** (`ncl_reg.vhd`): a 4-bit register captures 5 values
   through DATA→NULL 4-phase cycles with correct completion (`ko`) in nvc.
5. **Multi-stage pipeline handshake:** a 3-stage shift register (`pipe3`) flows 6
   values through 3 self-timed async stages (nvc, ~6 ns, no clock), and a 2-stage
   datapath with comb logic between stages (`pinc`) computes `q = d+1` self-timed.
   Fork extraction shows the per-stage request forks (`ki_in`, `~ko_s1`, `~ko_s2`
   each 8-way) — the handshake network.
6. **Cyclic/feedback desync** (`--reg desync`): an accumulator `r <= r + din` (which
   `--reg qdi` rejects as a feedback loop) is emitted as a stateless DIMS datapath +
   a matched-delay desync register and, in nvc, accumulates `sum mod 16` correctly
   over a sequence — self-timed, no clock.

## Not yet (the honest edges)

- `--reg desync` is **bundled-data** (a matched delay `TCOMB`), not pure QDI — it
  trades delay-insensitivity for the ability to hold state around a loop, which is
  the standard desynchronization trade. It collects all registers into one shared-
  clock bank (correct but conservative for designs with several independent loops)
  and targets VHDL (the register is a clocked process; a structural completion-tree
  form for fork extraction on feedback designs is future work).
- `qdi` cells are functional hysteresis models (100 ps gate delay), not
  characterized physical cells; physical P&R waits on TH-cell layout views (LEF/GDS).
