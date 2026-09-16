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
emits a **structural QDI register bank** (`../../lib/ncl_reg.vhd`): each bit's two
rails are TH22 C-elements gated by a shared 4-phase request `ki`, with completion
`ko` = a C-element chain over every bit's is-DATA. No clock — the delay-insensitive
handshake. This adds `ki`/`ko` ports and makes the request-distribution and
completion-tree forks extractable (they don't exist with the clocked `ncl_dff`).

## What run_struct.sh proves (on `add4`, a=b=4 bit → 5-bit sum)

1. **Fork extraction:** 17 gates → 68×th22 + 14×th12 + 10×th13 (DIMS survives
   `yosys flatten`); `constraints.py` enumerates **40 dual-rail isochronic forks**
   (a_L[i]/a_H[i]/b_L[i]/b_H[i] each fork), via its JSON-submodule-ports source —
   no LEF. Path set feeds layopt's `objective.fork_balance` exactly as the sync
   flow does.
2. **Functional:** the TH netlist (comb) decodes to `a+b` for all 256 inputs.
3. **Both VHDL bindings** analyze + elaborate in nvc.
4. **Structural QDI register** (`ncl_reg.vhd`): a 4-bit register captures 5 values
   through DATA→NULL 4-phase cycles with correct completion (`ko`) in nvc; a
   sequential RTL design (`reg4rtl.v`) emitted with `--reg qdi` yields the 8-way
   `ki` handshake fork (request distribution to every rail latch).

## Not yet (the honest edges)

- The QDI register bank is a SINGLE 4-phase stage with a shared `ki`/`ko`.
  Multi-stage pipeline handshake synthesis (stage N's `ki` = NOT stage N+1's `ko`,
  plus the request/ack network) is not yet generated from the netlist topology.
- `constraints.py` tags the `ki` request as an ordinary isochronic fork; a QDI-
  aware pass would classify handshake/completion forks as skew-tolerant (like
  clock distribution) rather than orphan-critical.
- `qdi` cells are functional hysteresis models, not characterized physical cells;
  physical P&R of the TH netlist waits on TH-cell layout views (LEF/GDS).
