# PIPES.md — The Pipe Construct in the NVC Fork

*2026-09-01 · drafted from LRM-grounded mailbox research and a channel-construct
survey, then adversarially critiqued (semantics, implementability) and revised.*

*Second draft · companion to `ASYNC-PLAN.md` (§3, §4) and `GPU-SIM.md` (§4).
Semantic spec, not implementation plan; LRM cites: IEEE 1800-2017 (SV), 1076
(VHDL), 1666 (SystemC). Revised against the semantic and implementability
critiques — resolutions on the page; closed and still-open decisions in §8.*

The pipe is the **executable counterpart of the channel contract**: what a
contract states about a boundary, a pipe simulates. Contracts *define*
(ASYNC-PLAN §3), bindings *refine*, pipes *execute* — one object per contract.

## 1. The pipe as executable channel contract

A pipe is a first-class, elaboration-time object: declarable in
architecture/block scope, connectable through ports, visible to the C frontend
— where the SV mailbox is `std` class glue: `new()`-allocated, no elaboration
identity, no ports, no `wait` sensitivity (1800-2017 15.2, 26.7, Annex G.4). A
non-port-connectable **dynamic tier** (§3.2) serves runtime-shaped mailbox
translation.

### 1.1 Configuration → contract fields

| Contract field | Pipe configuration | Notes |
|---|---|---|
| `encoding` | element type `T` of `pipe#(T)`; `byte`+stream framing for raw mode (§4.1) | representation (dual-rail, 1-of-N, valid/ready) lives in the binding; the pipe carries the abstract token stream all encodings refine |
| `completion` | token delivery at the delta-boundary update (§5.1) | bindings map the update event to rail-OR trees, matched delay, or clock edge |
| `ack` | put-side space grant (unblocking of a full `put`) | blocked `put` = withheld ack = deasserted ready; a signal-view boundary has no ack at all — it is a tap, outside the contract surface (§7.1) |
| `phase` | abstracted: one token per DATA wavefront, NULL/RTZ implied | 4-phase vs 2-phase is a binding property invisible at token level |
| `assumptions` | capacity, arbitration rule, visibility discipline (§5.1) — dischargeable assumptions only | machine-readable; emitted with the trace for (d). Semantic relaxations (coalescing, lossiness, timeout-dependence) are NOT assumptions — they reclassify the boundary (§1.2, §7.1) |
| `type` | `T`, 1:1; elements are values (deep-copied or immutable) | the log must denote data, not shared mutable state (§5.4); handle aliasing lives only in the SV shim's handle table (§3.1) |

### 1.2 Refinement conditions (ASYNC-PLAN §3 (a)–(d))

| Condition | Discharging pipe mechanism |
|---|---|
| (a) wavefront ordering | FIFO order of the deterministic event log (§5.4) |
| (b) data values | logged token values; the flow-equivalence checker (ASYNC-PLAN §4, Cortadella/Carloni) aligns these against golden traces |
| (c) local liveness | the pipe discharges only the **local no-starvation component**: every enabled blocked operation is eventually serviced under the published order (§5.3), under the contract's environment assumptions. Graph-level liveness — deadlock through cyclic channel dependencies — remains ASYNC-PLAN §4's composition-level check; the §5.3 quota and §2.4 blocked-time counters are detection aids, not discharge |
| (d) assumption discharge | declared capacity/arbitration/visibility parameters are recorded, dischargeable assumptions |

Refinement stays **boolean**: (a)–(d) hold or the binding is no refinement. A
boundary that coalesces, drops, or changes behavior on a fired `TIMEOUT` is a
tap outside the claim (§7.1), not a "weaker refinement"; a fired `TIMEOUT` on
a contract-bearing boundary is logged and drops it from the run's claim. The
graded lattice is declined; the P1 contracts ADR records or overturns this
(§8).

### 1.3 The elastic-buffer identity (normative)

**A bounded pipe with backpressure — stream view at both ends — IS the
sync-emulation binding of a channel.** `pipe#(T)(capacity => N)` simulates an
N-stage elastic buffer — Vortex's `VX_elastic_buffer` (ASYNC-PLAN §6):
occupancy = fill, blocked `put` = ready deassertion, delivery = `valid AND
ready`, `capacity => 0` = rendezvous (§5.2). Capacity is exact under both
visibility disciplines (§5.1); the signal view is *not* this binding (§7.1).
The §2.4 counters are the sync image of wavefront and ack activity, aligned by
the flow-equivalence checker; rebinding never changes the contract.

## 2. Object model and operations

### 2.1 Declaration and endpoints

A pipe declares element type `T`, `capacity` (required; `unbounded` is
explicit opt-in, §5.3), and **cardinality** (point-to-point default | MP | MC
| MPMC) — a second producer on a point-to-point pipe is a hard elaboration
error (the `sc_fifo` bind-check) — selecting the visibility discipline (§5.1).
Endpoints are directional handles (a producer cannot `get` — TLM-1, Go
`chan<-`); endpoint mode, **stream view** (full API) or **signal view** (§7),
is chosen at port association.

### 2.2 Operation set

| Operation | Blocks on | Non-blocking form | Results |
|---|---|---|---|
| `put(p, v)` | full | `try_put` | `OK`, `FULL`, `CLOSED` (error, §2.3) |
| `get(p, v)` | empty | `try_get` | `OK`, `EMPTY`, `EOF` |
| `peek(p, v)` | empty | `try_peek` | as `get`; non-destructive |
| `close(p)` | never | — | per-endpoint, either side, idempotent, refcounted |
| `flush(p)` | occupancy > 0 | — | blocking barrier: returns at occupancy zero, or `CLOSED` (the first draft's non-blocking "atomic drain" meant nothing under §5.1 — delivery needs a `get`) |
| `clear(p)` | never | — | atomic discard of buffered tokens |
| `select` | all arms blocked | `default:` arm | §2.5 |

Statuses are native enums (int codes live only in the SV shim, §3); every
blocking form takes an optional **timeout** (simulated time or delta count)
returning `TIMEOUT` (§1.2). All operations are atomic (normative);
kill-atomicity — a killed process leaves an operation fully done or never
begun — binds only where a process can die mid-operation (shim
`disable`/`kill`, foreign detach §6): VHDL cannot kill processes, so the core
kernel carries no dead obligation.

### 2.3 Close and EOF

Adopted from Go and POSIX — the gap every HDL precedent shares (mailbox,
`sc_fifo`, `tlm_fifo`, VUnit, OSVVM: none close); endpoints refcounted:

| Rule | Semantics |
|---|---|
| EOF = last producer close | consumers drain buffered tokens, then observe `EOF` forever — in-band, after-drain, a status, not an error; `try_get` distinguishes `EMPTY` from `EOF`. POSIX rule: MPMC close needs no coordinator. Bidirectional links are two pipes, so TCP-FIN half-close falls out free — exactly co-simulation shutdown at the GPU seam (§4.2) |
| `CLOSED` = EPIPE | `put` to a pipe whose last consumer closed, or via a closed endpoint, is a defined error naming the pipe — the alternative is silent deadlock. Close is legal from **either side**; the first draft's "producer-side" contradicted its own EPIPE rule |
| blocked ops at close | last-consumer close wakes every producer already blocked in `put` with `CLOSED`; last-producer close wakes every blocked `get`/`peek` — after drain — with `EOF`; both in §5.3 queue order, one delta after the close |
| signal view | signal-view endpoints never close and never block (§7.1): a pipe with a signal-view producer never reaches `EOF` — wires have no EOF — so a consumer needing `EOF` needs stream-view producers |

### 2.4 Introspection

`num`, `capacity`, `free`, `closed`, `at_eof`, blocked-endpoint counts,
high-water mark, cumulative blocked time, signal-view overrun count (§7.1) —
all sampled under the **same visibility rule as data** (§5.1): committed ⊕ the
caller's own operations on point-to-point pipes (read-your-writes: `num` after
your own `put` includes the token; "frozen" only ever meant independence from
other processes' intra-delta activity), live state on shared-endpoint pipes.
Defined sampling vs 15.4.2's "use with care"; `try_*` closes check-then-act
races.

### 2.5 Select / alternative

`select` waits on multiple guarded arms — `get`, `peek`, or `put` (output
guards are cheap in a single-threaded DES kernel; a deliberate superset of
occam, which excluded them for distributed-commit reasons). Default **PRI**:
textual priority, deterministic (occam `PRI ALT`); `fair` rotates via the
seeded RNG (bit-identical reruns); `default:` makes it non-blocking — retiring
the transaction-losing `fork/join_any`+`disable fork` workaround. v1: a
`capacity => 0` arm is ready only opposite a plainly blocked `put`/`get` —
select-facing-select across a rendezvous is diagnosed, its pairing rule
unpinned (§8).

## 3. Superset of the SystemVerilog mailbox

Verified: Vortex uses zero SV mailboxes — the shim is off the critical path,
but exact: "superset" means mechanical translation of clause 15.4, dynamic
allocation included. Shim pipes: always MPMC-immediate (§5.1), value-mode.

### 3.1 Translation table

| Mailbox (1800-2017) | Pipe equivalent | Delta from LRM behavior |
|---|---|---|
| `new(bound)`, static site | `pipe#(T)(capacity => bound)`; `new()` → `unbounded` | static negative bound = **elaboration error**, tightening 15.4.1's sanctioned indeterminate behavior (legal: the LRM calls it illegal) |
| `new(bound)`, runtime site | dynamic-tier pipe (§3.2) | bound checked at creation; negative = defined run-time error |
| `put(m)` / `get(m)` | `put` / `get` | identical blocking (15.4.3/15.4.5); dynamic shim raises run-time error on type mismatch |
| `try_put(m)` | `try_put`; shim int: >0 ok, 0 full | identical (15.4.4) |
| `try_get(m)` | `try_get`; shim int: >0 / 0 empty / <0 mismatch, message left queued | encoding preserved exactly — including the negative-is-truthy trap, so translated `if (mb.try_get(x))` misbehaves identically (15.4.6) |
| `peek` / `try_peek` | `peek` / `try_peek` | 15.4.7/8; the multi-unblock herd becomes the deterministic wake rule of §5.3(4) — every waiter on a non-empty pipe is serviced, so no translated code gains a deadlock; the LRM fixes no wake order |
| `num()` | `num` | strictly stronger: defined sampling with read-your-writes (§2.4) vs 15.4.2's disclaimer |
| untyped `mailbox` | `pipe#(dynamic)` — tagged-union shim, per-element runtime type tag | 15.4.5/15.4.9 preserved; typed is the default, dynamic exists only for translation |
| `put` of class handle | **shim handle table**: the element is an index into a shim-managed object table — a value, so the log denotes data (§5.4) | aliasing preserved for 1:1 translation; mutation through retained handles remains translated-SV behavior with SV's own 4.7 order dependence, confined to the shim — core pipes carry no reference mode (§1.1), so pipe determinism never rests on unpublished process order and a parallel kernel stays possible |

### 3.2 The dynamic tier

Mailboxes are constructed at run time — class constructors, loops, per fork
branch — so an elaboration-only pipe cannot host clause-15.4 translation.
Normative fix: the shim creates pipes at run time from a **deterministic
allocator**; IDs are `(creating process's elaboration ID, per-process creation
counter)` — reproducible under the deterministic scheduler, never heap
addresses — extending the §5.3 ID space and entering the log. Dynamic pipes
are MPMC-immediate, value-mode, neither port-connectable nor contract-bearing:
testbench objects. Translation of 15.4 is then total (process kill: shim
kill-atomicity, §2.2).

### 3.3 Guarantees preserved — and deliberately exceeded

| Guarantee | Mechanism |
|---|---|
| strict FIFO message order (15.4.3); FIFO service of blocked waiters in arrival order (15.4.5's one promise) | §5.3; the LRM's open choices — arrival order itself, 4.7 pick-order — the pipe *defines*, legally |
| same-timestep visibility, side channels included | shim pipes are MPMC-immediate (§5.1): a `put` sequenced before a named-event trigger, semaphore post, or shared-variable write is visible to the woken process in the same timestep — `put(x); ->e;` then the waker's `try_get` succeeds, as every conforming SV simulator requires. A uniform deferred commit could return `EMPTY` there — an outcome no SV simulator can produce, hence no refinement of 4.7; deferred commit is confined to point-to-point pipes, which the shim never emits. Read-your-writes: same-process put-then-`try_get` succeeds in one timestep under both disciplines (§5.1, §2.4) |
| same-timestep unblocking | a `put` makes a blocked `get` runnable in the same simulation time, one delta later, in a named phase (§5.2); clause 15.4 cites clause 4 nowhere, so any consistent choice conforms |

| Mailbox gap (evidence) | Pipe answer |
|---|---|
| no close/EOF — Annex G.4's eight methods are exhaustive; a blocked consumer deadlocks silently | §2.3 |
| no timeout; `fork/join_any`+`disable fork` workaround loses transactions | timeouts on every blocking op; shim kill-atomicity (§2.2) |
| nondeterministic consumer assignment (15.4.5 + 4.7) — fatal for golden traces | §5.3 total order |
| class-world only; no elaboration identity, no ports | first-class static object (§1); deterministic dynamic tier for parity (§3.2) |
| no broadcast; the `peek` herd is a race, not fan-out (15.4.7) | broadcast stays **out** of the core: a non-blocking tap/analysis port with bind-order subscriber iteration (`tlm_analysis_port` precedent) sits beside the pipe — the model for ack-less valid-only boundaries like Vortex `branch_ctl_if` (ASYNC-PLAN §6): an ack-less channel is a tap, and the signal view (§7.1) is the signal-port-shaped member of the same family |
| unbounded default + zero-time producer = livelock | bounded default + delta-quota diagnostic (§5.3) |
| int-coded errors, negative-truthy trap | native status enums; ints confined to the shim |

## 4. The byte pipe: sockets, the C frontend, the GPU seam

### 4.1 Byte view and POSIX/TCP equivalence

Every `pipe#(T)` exposes a **raw-byte view**: the token stream through `T`'s
canonical byte encoding (pinned layout and endianness — normative; bytes cross
the C and GPU seams). The byte view is a *stream* — message boundaries need
explicit framing; pipe-of-bytes ⊆ pipe-of-T is a specialization, not the
foundation — the element type, not a stringly encoding, maps 1:1 onto the
contract `type` field. Its degenerate case, `pipe#(byte)` in stream mode,
adopts the POSIX pipe / TCP socket contract verbatim — unretrofittable, so
adopted from day one:

| Socket concept | Byte-pipe semantics |
|---|---|
| short read/write | normal outcomes in the signature (counts ≤ requested), never errors |
| flow control (rwnd) | bounded capacity = credit; blocked write = zero window; **backpressure IS flow control** |
| `PIPE_BUF` atomicity | a stated atomicity unit for multi-producer writes; larger writes may interleave |
| EOF (`read()` = 0) / FIN half-close | after-drain, in-band, when the last writer closes — **EOF IS close**; half-close = pipe pairs (§2.3) |
| EPIPE/SIGPIPE | defined `CLOSED` error naming the pipe |
| readiness (`poll`) | non-blocking poll in the C API (§6) |
| reconnect | **not adopted** — an elaborated foreign endpoint has one connection lifetime (`EOF` permanent, no `accept()`); listener-style sequential connections and restarting peers reattach on fresh dynamic-tier pipes (§3.2), never by resurrecting a closed one (reattach API: §8) |

This is the C-frontend channel representation: via the §6 API a channel
into the simulation is a socket-shaped object; a real TCP/Unix-socket
transport behind it is a transport swap, not a semantic change — and typed
pipes reach C via the canonical encoding.

### 4.2 The NVC↔GPU co-simulation seam

The seam is a byte-pipe pair carrying GPU-SIM §4's **windowed protocol**
(events become data; event control stays on the host) as a two-phase
**grant/return/commit** exchange — an append-only merge cannot express its
"re-solve short windows from checkpoints":

| Phase | Rule |
|---|---|
| **grant** | host issues a window: time horizon + event/byte credit (TLM-2.0 temporal decoupling plus TCP credit flow control). The horizon is **conservative** — bounded by the minimum next host event / provable lookahead (Chandy–Misra), never optimistic or wall-clock-derived |
| **return** | GPU returns per-island crossings for the window — **provisional**, not yet in the log |
| **commit** | no host reaction inside the window ⇒ host commits; only then do crossings merge into the event log (§5.4) under the total key `(time, island_id, seq)`. A host reaction feeding back into an island before the horizon ⇒ re-grant from the checkpoint at the crossing time, provisional state discarded. Only committed windows reach the log; committed state never rolls back — the TLM quantum's determinism trade stays rejected |

Determinism is a **requirement on the GPU kernels**, not a free property of
the protocol: deterministic reduction order (GPU-SIM §1's atomic crossing
lists sorted before return), returned arrays in total-key order, crossing
times quantized to a **pinned grid** (the shape of the answer to GPU-SIM Q3;
the value is §8's), exactly re-solving checkpoints; the recorded window
schedule makes reruns regroup bit-identically. Across *different* schedules
regrouping can move a crossing within a grid cell: "window size has zero trace
effect" is **withdrawn** — window size is a performance knob, its trace effect
grid-bounded and checked by the EC tolerance rule. A GPU build that cannot
meet these requirements mounts under §6 record-replay, golden traces
per-recording.

## 5. Time and determinism

Bit-identical reruns are a hard EC requirement: the event log (§5.4) is a pure
function of design + stimulus + recorded run configuration (§4.2, §6).

### 5.1 Visibility: two disciplines, both deterministic

A single frozen-visibility rule is unsound for shared endpoints: two
same-delta producers on a capacity-1 pipe each see committed-empty, both
return `OK`, and the commit overruns capacity; returned statuses cannot be
revised at commit, and §5.3 governs only *blocked* ops. So:

| Cardinality | Rule |
|---|---|
| point-to-point: **deferred commit** | state visible to process P = committed state at the last delta boundary ⊕ P's own operations this delta (the `sc_fifo` evaluate/update discipline, IEEE 1666); pending gets commit before pending puts at the boundary (§5.3(5)). Exact with one producer and one consumer: gets touch only committed tokens; the producer's free-space view is conservative against same-delta gets. Cross-process behavior independent of intra-delta order — the VHDL signal guarantee (1076 cl. 14) extended to pipes. Cost: no same-delta cross-process handoff; a chain of N stream pipes adds N deltas per token (fusion excepted, §7.2) |
| MP / MC / MPMC: **immediate state** | operations act on live shared state, sequenced by the published intra-delta process order (§5.3(2)). Capacity and statuses exact at every call; a token may cross within one delta when process order permits. The SV-mailbox visibility model with 1800 4.7's nondeterminism replaced by a published total order — why the shim uses it (§3.3) |

The split mirrors ASYNC-PLAN §4: point-to-point boundaries are the
Kahn-deterministic ones and get order-independence; arbitrated boundaries —
where sync-binding verification does not transfer — get a published order
instead, recorded as a contract assumption (§1.1).

### 5.2 Blocking, deltas, and simulated time

Blocking costs zero simulated time. `wait until can_get(p)` is a **native
scheduler wake condition** — the pipe is not sugar over a hidden signal plus
protected type (the §7.3 workaround). A `put` enabling a blocked `get` makes
it runnable next delta, resumed right after signal update; blocked operations
may span time advance. `capacity => 0` is rendezvous, pinned — never
`tlm_fifo`'s size-0 "both full and empty": `put` and `get` pair, the token
commits at the boundary, the reader resumes next delta.

### 5.3 Arbitration: a specified total order

Everything 1800-2017 15.4 + 4.7 leave open is resolved normatively:

| # | Rule |
|---|---|
| 1 | endpoint IDs: elaboration in instance-path lexical order for static pipes; deterministic creation order for dynamic-tier pipes (§3.2) — never heap addresses or hash order; stable across runs and builds |
| 2 | within a delta, runnable processes execute in ascending process elaboration ID — published and normative, because immediate-state pipes (§5.1) make intra-delta order observable |
| 3 | blocked operations queue FIFO by arrival `(time, delta)`; ties break by ascending endpoint ID |
| 4 | **wake rule** (the 15.4.7 herd, terminated correctly): at each delta boundary, while the pipe is non-empty, the blocked-waiter queue is serviced in order — peekers observe without consuming, getters consume — stopping only when the pipe is empty or the queue exhausted. A getter may consume the last token and legally leave a later peeker blocked (SV-permitted); an `EOF`/`CLOSED` transition wakes all remaining waiters with that status (§2.3). One-wake-per-token would deadlock translated 15.4.7 code; this rule forbids it |
| 5 | deferred-commit pipes commit pending gets before pending puts at the boundary; immediate pipes take effect in rule-2 order at the call |
| 6 | `select` is PRI by textual order; `fair` draws from the seeded RNG (§2.5) |

Go randomizes `select` because observable order breeds silent dependence; a
golden-trace flow pins it: published, reproduced by every conforming build,
recorded under `assumptions`. Zero-time-loop protection: bounded capacity is
the default, `unbounded` explicit opt-in (Go refuses it; the mailbox default
pushes livelock to the user), plus a per-pipe delta quota — N deltas sustained
without time advance is diagnosed, naming pipe and processes: detection aid,
not discharge (§1.2).

### 5.4 The event log

Pipe observable semantics ARE a totally ordered log of `(time, delta, seq,
endpoint_id, op, value)` — at once (a) the definition of behavior (runs are
equivalent iff logs are identical); (b) the golden trace the flow-equivalence
checker aligns; (c) the committed-window record crossing the GPU seam (§4.2).
Trace capture is a filter over the log.

## 6. Foreign endpoints (VHPI / DPI / socket)

One end of a pipe may live outside the simulator:

| Rule | Content |
|---|---|
| first-class kernel interface | the pipe C API is not an application of NVC's VHPI layer: per-endpoint wakeup callbacks pinned to a **named phase** of the simulation cycle (a vocabulary this spec defines — VHDL has none), firing same-phase in endpoint-ID order (§5.3) — closing cocotb's documented leak (same-time trigger fire order "implementation-defined, will vary by simulator"). VHPI (VHPIDIRECT/foreign subprograms), the DPI shim for SV co-sim, and the socket transport are **mounting shims over this interface**, not the machinery it rests on. The API is non-blocking by construction (a blocking callback halts the simulator): `pipe_read` / `pipe_write` / `pipe_poll`, short transfers normal (§4.1) |
| external-source contract | what a DES kernel cannot improvise: an empty event queue jumps time straight past a socket that has produced no bytes, and the wall-clock drain of a full transport is itself an event needing a stamp. A mounted transport therefore registers a **bounded time-advance horizon** and must re-arm it before the kernel may advance past it — structurally the §4.2 window grant, deliberately the same mechanism: a plain socket and the GPU engine are one kind of seam. Transports are polled at named-phase points; arrivals *and* drain notifications are stamped there as external events entering the log |
| record/replay | the **recorded log is itself a mountable transport**: replay is a mount-time switch, not a bolted-on mode — reruns replay bit-identically; live re-runs may differ |

## 7. Signal-port polymorphism: the signal view

### 7.1 Semantics — the signal view is a tap, not a binding

Load-bearing requirement: a VHDL entity attaches to a pipe through an ordinary
signal port **with the entity code unchanged** — a wire replaced by a one-bit
pipe; endpoint mode is chosen at port association (§2.1) — the
simulation-level mirror of per-boundary binding. But the signal view is
**not** the first draft's "sync-emulation binding": it merges equal-valued
tokens at *any* consumer speed (same-value assignment raises no event), so a
stream→signal→stream round trip changes the token stream — refinement (a)/(b)
violations, not weakenings. The signal view is the **wire/broadcast
abstraction — a signal-port-shaped tap** (§3.3); per ASYNC-PLAN §4's
non-channel-signal convention it is **outside the EC surface** unless explicit
token framing (companion toggle/valid, or per-token delta separation) lifts it
back to a channel; unframed, it is a declared observation point.

| Rule | Semantics |
|---|---|
| producer: **one token per signal event** | per delta in which the driving value changes, stamped `(event time, event delta)` at that update phase; stream-view consumers receive it per §5.2. Same-value re-assignment: a transaction, no token (1076 event semantics) |
| producer vs full pipe | a signal-view producer can never block or see a status: the **oldest queued token is dropped for the newest** (latest-wavefront), the overrun counter increments (§2.4), and the contract records the boundary as lossy toward stream consumers — capacity never exceeded, the wire never backpressured; declared-lossy, not silently unbounded. A boundary that must not coalesce keeps a stream-view producer |
| consumer: **latest delivered value** | each token updates the port at the delta boundary; an event occurs iff the value changes. Delivery auto-drains — no backpressure, occupancy never accumulates; a slow consumer observes the latest wavefront, as a wire does |

### 7.2 Conservativity by fusion (normative)

A pipe with signal view at **both** ends shall **elaborate to the plain signal
it replaced** — the adapters compile away (NVC's port-collapsing machinery).
Fusion is forced: a live pipe delivers at d+2 where the wire delivers at d+1 —
the first draft's off-by-one — and zero-delta transit would contradict §5.1.
Consequences:

| Case | Rule |
|---|---|
| both ends signal view (fused) | values, events, delta timing, initial values, resolution (the singleton call on a resolved single-driver signal included), and `'transaction`/`'quiet`/`'last_active`/`'last_event` are exactly the signal's — it *is* the signal. Log tokens are synthesized from the net's events; introspection is degenerate (occupancy 0). The conformance suite's wire-vs-pipe trace diff passes trivially: same object |
| first endpoint upgraded to stream view | §5.1's one-delta cost appears here — a declared, elaboration-reported timing change, not a silent one |
| mixed view (one stream, one signal end) | conservative for **values and events only**; the transaction-class attributes above are enumerated as *not preserved*. Non-identity resolution on a replaced single-driver signal routes to the §8 multi-driver decision |
| initial values | transfer out-of-band: the consumer-side port initializes from the producer's initial driving value at elaboration; the initial value is not a token, and a first assignment equal to it produces none — documented, not discovered |

### 7.3 Mechanism: NVC-fork object class (decided), full extension surface

The pipe is a **fourth object class** alongside signal, variable, and file.
Rejected: **VHDL-2019 mode views** — direction projections that cannot express
token generation, blocking, or delta semantics, and demand view-typed ports,
violating "entity code unchanged". Rejected: **resolution-function encoding**
(OSVVM-style resolved records over a protected type) — standard-VHDL-buildable
and exactly the cautionary tale: wiring errors resolve to silent garbage,
processes cannot wait on protected-type state (VUnit's global-`net` hack),
determinism accidental. Only the kernel can implement §5 as stated.

Honest cost, fully enumerated — "confined to declarations and associations"
undersold it: (1) pipe declarations and port associations, with implicit view
adapters at signal-mode formals; (2) a **pipe parameter object class** for
subprograms — without it no reusable procedure or BFM can take an endpoint;
(3) **wait sensitivity on pipe predicates** (`can_get`, `can_put`), mixed
conditions included; (4) the **`select` statement**, new sequential-statement
grammar; (5) a pipe on an `inout`/`buffer` formal: v1 elaboration error, named
diagnostic. Entities remain standard VHDL; strict-portable mode macro-expands
pipes to the resolution-function encoding for export, whose degraded semantics
argue *for* the native class.

## 8. Open decisions

- Resolved-signal replacement: multi-driver (MP + resolution hook, or out
  of scope), plus non-identity resolution on a single driver (§7.2).
- Whether the P1 ADR ratifies boolean refinement with taps outside the
  claim (§1.2) or defines a graded lattice with per-level EC obligations.
- Tap/analysis-port API surface (subscriber granularity, lossy policies).
- `select` output guards in v1 or input-only first; the deferred
  rendezvous select-vs-select matching rule (§2.5).
- SV-frontend surface: DPI shim only, or a native pipe in the SV reader;
  dynamic-typed shim always available, or behind a translation flag.
- Values to pin: composite-`T` byte encoding (§4.1; here or the P1 ADR),
  delta quota N (§5.3), the GPU crossing-time grid (§4.2 — settles Q3).
- Foreign reattach API (§4.1): sequential connections on fresh dynamic
  pipes.

Closed since the first draft, not to be re-litigated: `'transaction` fidelity
(fusion, §7.2); reference element mode (dropped — shim handle table, §3.1);
dynamic mailbox translation (§3.2); signal-view-as-sync-binding (tap, §7.1);
GPU window-size "zero trace effect" (withdrawn, §4.2); the single visibility
rule (split by cardinality, §5.1); non-blocking `flush` (§2.2).