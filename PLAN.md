# Mylex — Project Plan

**Mylex** is an open-source ONNX-to-Verilog-AMS compiler, part of the Cameron
EDA SNN synthesis stack. It consumes ONNX (with QONNX quantization
annotations) and NIR (Neuromorphic Intermediate Representation) as inputs, and
emits standard Verilog-AMS referencing an accompanying primitive library.

License: PolyForm Noncommercial 1.0.0 for the tools in this repository
(see `LICENSE-ASYNC.md`; decided 2026-09-01, superseding the BSD-3-Clause
plan below where they conflict). Code derived from NIR upstream (reference
models, reused tests) remains BSD-3-Clause per its origin.

This document is the working plan, not the spec. Decisions get refined in the
VM during implementation; this exists to keep the architecture coherent and
prevent scope drift.

---

## 1. Strategic context

Mylex exists because:

1. **NeuroBench/THOR submission.** Provides a forcing-function deadline
   (2026-07-24) and a recognized benchmark (OpenBMI motor imagery) for the
   first end-to-end demonstration.
2. **NIR backend membership.** No existing NIR-compatible backend targets
   general-purpose silicon (FPGA, sync ASIC, async ASIC, mixed-signal). The
   five current hardware backends (Loihi 2, SpiNNaker2, Speck, Xylo,
   BrainScaleS-2) are all single-paradigm dedicated neuromorphic silicon.
   Mylex aims to be the first multi-paradigm NIR backend.
3. **ONNX as on-ramp.** ONNX is the industry-recognized format; NIR is the
   technically correct internal IR for spiking semantics. Mylex accepts both,
   uses NIR-style primitives internally, and is positioned as "ONNX
   synthesizer for design classes conventional HLS (hls4ml, FINN) cannot
   reach" — async, mixed-signal, event-driven, sparse-activation.
4. **Commercial follow-on.** Mylex is the open frontend; the Verilog-AMS →
   silicon synthesis pass is a separate commercial NVC plug-in (out of scope
   here). The format boundary is standard Verilog-AMS, which anyone can
   consume; the commercial value is in synthesis quality.

## 2. Scope

### In scope
- ONNX graph parsing (operator subset, see §5)
- NIR graph parsing via the upstream `nir` Python package
- Internal IR based on NIR's 17 primitives plus structural extensions
- Verilog-AMS emission referencing a primitive library
- Verilog-AMS primitive library (`lib/`) — the load-bearing artifact
- CLI: `mylex input.onnx -o output.vams`
- Verification harness against NIR reference models
- QONNX quantization metadata preservation through to emitted AMS parameters

### Out of scope (this repo)
- Synthesis of Verilog-AMS to gates, FPGA, or silicon
- Training (assumes pre-trained models as input)
- ANN-to-SNN conversion (rate coding, threshold balancing)
- NVC fork integration (lives elsewhere; Mylex emits standard AMS)
- Runtime respecialization (lives in NVC + ldx)

## 3. Architecture

```
ONNX file ──┐
            ├──► Frontend ──► Internal IR ──► Backend ──► Verilog-AMS + netlist
NIR (.h5) ──┘     (parsers)    (NIR-shaped)    (emitter)
                                                          │
                                                          ▼
                                                    lib/*.vams
                                                  (primitive library,
                                                   referenced by emission)
```

### Layer responsibilities
- **Frontend.** Parse external format → internal IR. ONNX reader walks the
  protobuf graph; NIR reader is a thin wrapper over `nir.read()`. Both
  produce the same internal IR.
- **Internal IR.** NIR primitives extended with chip-design-relevant nodes
  where needed (TBD; see §6). Graph-walk-friendly Python objects.
- **Backend.** Emit Verilog-AMS module per primitive instance, generate a
  top-level netlist module that wires them together using the graph's edges.
  References (does not inline) the primitive library.
- **Library (`lib/`).** Hand-written Verilog-AMS modules implementing each
  NIR primitive's mathematics. The compiler does not generate these; they
  are the substantive engineering artifact and are verified against the
  reference NIR implementations.

## 4. The primitive library (`lib/`)

NIR defines 17 primitives. After accounting for compositional definitions
(`CuBa-LIF = LI ; Linear ; LIF`, `IF = Integrator ; Threshold`, etc.) and
structural-only nodes (Input, Output, Flatten), the **unique mathematical
implementations** required are:

| Module             | Verilog-AMS shape                    | Notes                          |
|--------------------|--------------------------------------|--------------------------------|
| `li.vams`          | `analog` block, single ODE           | τv̇ = (v_leak − v) + R·I       |
| `integrator.vams`  | `analog` block, single ODE           | v̇ = R·I                       |
| `threshold.vams`   | `@(cross(...))` event emitter        | δ(I − θ_threshold)             |
| `linear.vams`      | Discrete, spike-driven MAC           | W·I                            |
| `convolution.vams` | Discrete, spike-driven conv          | f ⋆ g, parameterized           |
| `delay.vams`       | Discrete shift register / delay line | I(t − τ)                       |
| `scale.vams`       | Discrete multiplier                  | s·I                            |

Composite primitives (`lif.vams`, `cuba_lif.vams`, etc.) instantiate the
above primitives and wire them according to NIR's compositional definitions.
This keeps the library DRY and ensures the mathematical equivalence to
NIR's specification is visible in the source.

**Verification strategy.** Each `.vams` module has a corresponding test that
runs the NIR reference Python implementation on a fixed input sequence,
runs the AMS module under NVC (or any AMS-aware simulator), and compares
outputs within tolerance. The reference implementations live at
github.com/neuromorphs/NIR in `nir/ir/` (BSD-3-Clause).

## 5. ONNX operator support

First-cut operator coverage, prioritized by what's actually needed for the
THOR submission and standard small-model testing:

**Tier 1 (MVP):**
- `MatMul`, `Gemm` → `Linear` / `Affine`
- `Add` (bias) → folds into `Affine`
- `Conv` → `Convolution`
- `Relu`, `Sigmoid`, `Tanh` → annotated as activations (mapped to threshold-
  like primitives or dropped for SNN models)
- `Reshape`, `Flatten`, `Squeeze`, `Unsqueeze` → `Flatten`-equivalents
- QONNX `Quant`, `BipolarQuant` → quantization metadata on adjacent ops

**Tier 2 (nice-to-have):**
- `AveragePool`, `MaxPool` → `AvgPooling` (Max becomes `SumPooling` + activation)
- `BatchNormalization` → folds into `Affine` (constant-fold at compile time)
- `Concat`, `Split` → graph-structural

**Tier 3 (later, or refuse):**
- `Loop`, `If`, `Scan` — control flow, defer
- Anything with dynamic shapes — refuse with diagnostic
- `Transformer`/attention-specific ops — defer to ANN-specific roadmap

SNN custom ops (from snnTorch, Sinabs ONNX exports) are recognized
opportunistically when their names match known patterns, but the canonical
SNN path is via NIR, not ONNX-with-custom-ops.

## 6. Internal IR

Start with NIR's 17 primitives as the IR's primitive set, plus an extension
mechanism. Extensions likely needed during this project (proposed upstream
to NIR if they prove general):

- **Memory primitives:** `Register`, `FIFO`, `RegisterFile` — for stateful
  computations that don't fit the LIF/LI mold.
- **Routing:** `Mux`, `Demux`, `Arbiter` — for cluster-to-cluster spike
  routing in larger models.
- **Quantization annotations:** carry QONNX bit-width, scale, zero-point as
  metadata on primitive nodes; the backend uses these to emit fixed-point
  parameters.

Extension policy: implement as needed, document in `docs/extensions.md`,
propose upstream where general (NIR maintainers are receptive — paper
explicitly acknowledges "the present set of primitives is limited").

## 7. Test sources

### Canonical SNN reference models (Tier 1 — must pass)
- **NIR reference models** at
  [github.com/neuromorphs/NIR](https://github.com/neuromorphs/NIR), in the
  `paper/` directory. Three SNN graphs of varying complexity, used to
  validate the original Nature Communications paper across all 11 NIR
  platforms. These are the canonical "does Mylex correctly implement NIR
  semantics" tests. BSD-3-Clause.
- **NIR test suite** in `tests/` of the same repo — unit tests for each
  primitive. Reusable as Mylex's primitive-verification harness.

### Standard ONNX dense models (Tier 1 — toolchain validation)
- **MNIST** from the ONNX Model Zoo (migrated to
  [huggingface.co/onnxmodelzoo](https://huggingface.co/onnxmodelzoo) after
  github.com/onnx/models stopped LFS hosting on 2025-07-01). Tiny, canonical,
  validates basic ONNX parsing.
- **SqueezeNet** or **MobileNet-v2** from the same source. Small enough to
  flow end-to-end, exercises Conv/Add/Mul/Pool/BatchNorm ops.

### Quantized ONNX models (Tier 2 — competitive positioning)
- **QONNX model zoo** at
  [github.com/fastmachinelearning/qonnx](https://github.com/fastmachinelearning/qonnx)
  in the `qonnx_model_zoo` subdirectory. These are the models hls4ml and
  FINN target; supporting them is the differentiation point against those
  tools.

### THOR-specific (Tier 1 — submission target)
- **OpenBMI EEG motor imagery dataset.** Referenced from the THOR
  NeuroBench Challenge 2026 documentation. Dataset access via the NeuroBench
  harness; pre-trained reference SNN models for the task come from training
  via snnTorch or Norse, exported through NIR. This path is:
  `snnTorch (train) → NIR (export) → Mylex (compile) → Verilog-AMS → NVC
  (simulate) → ZCU104 (deploy) → NeuroBench (measure)`.

### SNN framework examples (Tier 3 — robustness)
- snnTorch tutorials' pre-trained models, exported via NIRTorch.
- Norse pre-trained models, exported via Norse's NIR support.
- Sinabs example models for the Speck chip, exported via Sinabs' NIR support.

These exercise corner cases the canonical references don't catch.

## 8. Repository structure (first commit)

```
mylex/
├── README.md
├── LICENSE                          BSD-3-Clause
├── pyproject.toml
├── docs/
│   ├── PLAN.md                      this document
│   ├── extensions.md                IR extensions beyond stock NIR
│   └── primitives.md                AMS library spec
├── mylex/
│   ├── __init__.py
│   ├── ir/
│   │   ├── __init__.py              IR primitive classes
│   │   └── graph.py                 Internal graph representation
│   ├── frontend/
│   │   ├── __init__.py
│   │   ├── onnx_reader.py
│   │   └── nir_reader.py
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── verilog_ams_emitter.py
│   │   └── netlist.py               Top-level wiring emitter
│   └── cli.py
├── lib/                             Verilog-AMS primitive library
│   ├── li.vams
│   ├── integrator.vams
│   ├── threshold.vams
│   ├── linear.vams
│   ├── convolution.vams
│   ├── delay.vams
│   ├── scale.vams
│   ├── lif.vams                     composite: LI + Threshold
│   ├── if_neuron.vams               composite: Integrator + Threshold
│   ├── cuba_li.vams                 composite: LI + Linear + LI
│   └── cuba_lif.vams                composite: LI + Linear + LIF
├── tests/
│   ├── primitives/                  per-primitive verification
│   ├── reference_models/            NIR's three reference graphs
│   ├── onnx/                        ONNX parsing tests
│   └── e2e/                         end-to-end small models
└── examples/
    ├── mnist/
    ├── nir_reference/
    └── openbmi/                     THOR submission scaffold
```

## 9. Milestones

Loose ordering, not a Gantt chart — actual sequencing depends on what
turns out to be load-bearing first.

**M0: Scaffolding (week 1).** Repo structure, README, LICENSE, pyproject,
empty package skeleton, CI setup. First commit.

**M1: Primitive library MVP (weeks 2–3).** `li.vams`, `threshold.vams`,
`lif.vams` written and verified against NIR reference Python
implementations. Establishes the verification methodology that the rest of
the library follows.

**M2: NIR frontend + AMS backend MVP (weeks 3–4).** Reads an `.h5` NIR
graph containing a single LIF neuron, emits a Verilog-AMS top-level that
references `lib/lif.vams`. End-to-end through NVC. The minimum viable
demonstration of the architecture.

**M3: Full primitive library (weeks 4–6).** All seven unique math
modules + all composite modules. Each verified against NIR reference. This
is the bulk of the engineering work.

**M4: NIR reference models pass (weeks 6–7).** Mylex compiles all three
NIR paper reference graphs end-to-end with output matching the reference
Python implementation within tolerance. This is the "we're a real NIR
backend" milestone.

**M5: ONNX frontend Tier 1 (weeks 6–8, parallel with M4).** MatMul, Conv,
Gemm, Reshape, basic ONNX MNIST runs end-to-end. Mostly mechanical once
the IR is solid.

**M6: THOR submission package (weeks 7–8).** OpenBMI model trained
externally (snnTorch), exported via NIR, compiled by Mylex, simulated in
NVC, deployed to ZCU104, measured via NeuroBench harness. Submission by
2026-07-24.

**Post-deadline:** QONNX support, IR extensions, second-board (D5005)
validation, runtime tuning integration with ldx.

## 10. Risk register

- **Training pipeline ownership.** Mylex doesn't train; somebody has to
  train the OpenBMI model in snnTorch and export it. Calendar-critical for
  THOR submission. Mitigation: this can run in parallel with M3–M5, or use
  a pre-trained reference model from the snnTorch tutorial set as a fallback
  if the OpenBMI training is delayed.
- **NVC Verilog-AMS subset.** Mylex emits standard Verilog-AMS, but the
  RNM recognition in the NVC fork has to actually handle what Mylex
  generates. Tight coupling between the two projects. Mitigation: keep
  Mylex's emitted AMS minimal and standard; bring up NVC RNM recognition
  in parallel and treat the AMS subset as a contract between the two
  projects.
- **NIR primitive coverage edge cases.** Some NIR primitives have
  parameter combinations the spec doesn't fully constrain (e.g., reset
  behavior corner cases). Mitigation: defer to NIR reference Python
  behavior as ground truth; document divergences.
- **ZCU104/D5005 bring-up.** Toolchain (Vivado/Vitis, Quartus Pro,
  PetaLinux, OPAE) is non-trivial and parallel to Mylex development.
  Mitigation: ZCU104 bring-up is on the critical path for M6; D5005 is
  Phase 2 / post-deadline.

## 11. Open decisions

The following are deliberately not pinned down in this document and will
be made during implementation:

- HDF5 schema for emitted netlist auxiliary data (weights, quantization
  parameters): inline in `.vams` as parameters, or separate `.h5`?
- Verilog-AMS port-naming convention for spike events vs. continuous
  signals — needs to be consistent across the library before too many
  modules commit to a choice.
- How aggressively to constant-fold in the frontend (e.g., BatchNorm into
  Affine) — affects what reaches the backend and what synthesis sees later.
- Whether to emit one `.vams` file per primitive instance or one per graph
  (probably the latter, but the choice affects emitter complexity).

These get pinned down in `docs/decisions/` as they're made, ADR-style.
