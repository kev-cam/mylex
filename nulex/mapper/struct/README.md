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

`th_cells.vhd` carries both architectures per cell (`comb`/`qdi`); a third
`phys` (SG13G2/logic3da) binding is future work.

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
Register feedback (a cyclic register dependency, e.g. an accumulator) is rejected
— async desync of cyclic logic is out of scope.

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

## Not yet (the honest edges)

- Only **feed-forward** pipelines. A cyclic register dependency (accumulator,
  state machine with feedback) is rejected — async desynchronization of cyclic
  logic is a deeper problem out of scope here.
- `constraints.py` tags the `ki` request as an ordinary isochronic fork; a QDI-
  aware pass would classify handshake/completion forks as skew-tolerant (like
  clock distribution) rather than orphan-critical.
- `qdi` cells are functional hysteresis models (100 ps gate delay), not
  characterized physical cells; physical P&R waits on TH-cell layout views (LEF/GDS).
