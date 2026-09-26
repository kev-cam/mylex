#!/usr/bin/env python3
"""polysynth -- synthesize one block every viable way, score each variant with the
campaign's MEASURED cost models under a named workload, emit a comparison table
and a pick.

    polysynth.py <rtl-or-netlist> <top>
        [--workload <module>@<kernel>[,<module>@<kernel>...]]   (permodule.json)
        [--duty D --alpha A [--alpha-ff F] [--burst B] [--ncyc N]]  (explicit vector)
        [--out <dir>] [--vcd <file> --vcd-scope tb/dut --op-ns 10]
        [--gt sha_slice|alu_top] [--json <out.json>] [--verify]

EMPIRICAL SELECTION.  The SELECTION-RULE.md hard gates (G-A..G-E) act as a
PRUNER -- a structurally-illegal variant is never built -- but the DECIDER is
the measured-model score under the workload vector.  Every figure printed is
labelled MEASURED / COMPOSED / DERIVED / ASSUMED and every variant EMITTABLE /
ANALYSIS-ONLY / INVALID-AS-EMITTED.  UNDECIDABLE is a valid pick.

WHAT IS REUSED (nothing re-derived; the sum-of-pieces trap is why):
  shared IR       yosys generic-gate JSON, the recipe of nulex/mapper/alu/synth_alu.ys
  sync binding    run_synth.sh recipe (sequential) / the threeway generic+abc route
                  (combinational -- reproduces work/sha_slice.cmos.v byte-identical);
                  OpenSTA for cells/area/critical path (+liberty power when --vcd)
  QDI binding     nulex map_ncl_direct.py (word-level cones) or map_ncl_direct_gl.py
                  (gate-level tiling, --maxgates 1 = the committed campaign variant);
                  ring registers = the committed regstage template (byte-identical)
  DIMS contrast   nulex map_ncl_struct.py, labelled INVALID-AS-EMITTED (the ALU DIMS
                  netlist never ran: constant-pinned hysteretic cells cannot RTZ)
  QDI cost model  stat-sim qal/synth/threeway/compose_alu.py (same arc models as
                  compose_async.py, whole-netlist costing)
  sync cost model vortex_energy/compose_energy.py coefficients (imported; its own
                  instrument check runs at import and aborts if the composer drifts)
  QAL model       compose_qal_alu.py constants (measured 1.343 fJ/gate-settle,
                  wp-weighting, switch-tax band, ZCD 30-300 fJ ASSUMED) + the
                  SELECTION-RULE.md section-3 bank-partition DP (max-min bank, span<=4)
  workloads       /home/claude/vortex_energy/permodule.json (real-run duty/alpha/burst)
"""
import argparse
import collections
import contextlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys

THREEWAY = "/usr/local/src/stat-sim/qal/synth/threeway"
NULEX = os.path.dirname(os.path.abspath(__file__))
VE = "/home/claude/vortex_energy"
LIB = ("/usr/local/src/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/"
       "sg13g2_stdcell_typ_1p20V_25C.lib")
PERMODULE = VE + "/permodule.json"

sys.path.insert(0, THREEWAY)
sys.path.insert(0, NULEX)
import compose_alu as CA              # QDI/DIMS whole-netlist cost engine
import compose_qal_alu as CQ          # QAL measured constants + liberty/width readers
import cost_inputs as CI              # SPICE-gold liberty pin caps
import map_ncl_struct as MS           # pipeline_stages() = hard gate G-A
import map_ncl_direct as MD           # MAXSUP = hard gate G-B threshold

# QAL admission thresholds (SELECTION-RULE.md section 3, Ov(N)-floor arithmetic)
NMIN_WORKING, NMIN_CONFIDENT, NMIN_UNDECIDABLE_HI = 50, 150, 400
BANK_SPAN = 4                          # d <= 4 level-span cap (D5; RC_g-anchored)
BURST_AMORTIZED = 20                   # fill/drain amortizes at B >~ 20 (section 3)
HURDLE = {"BD": 1.3, "QDI": 2.0, "QAL": 3.0}   # section 3 hurdle rates
TH_LEAK_BAND_W = (58.5e-12, 155.7e-12)  # W/cell, state/mix-dependent band
                                        # (SELECTION-RULE.md section 6 -- ASSUMED band)
BD_DELAYLINE = (0.012, 0.017)          # delay line 1.2-1.7% at real W_eff [M, retraction
                                        # of the small-block artifact; SELECTION-RULE 7]

CE = None                              # compose_energy, imported lazily (it self-checks)


def load_CE(outdir):
    """Import vortex_energy/compose_energy.py.  Its module body recomputes the whole
    energy map and runs its own instrument check (aborts >2% vs the measured
    46.671 pJ/op anchor) -- importing it IS a live validation of the sync composer."""
    global CE
    if CE is not None:
        return CE
    sys.path.insert(0, VE)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        import compose_energy as _ce
    CE = _ce
    open(os.path.join(outdir, "compose_energy_import.log"), "w").write(buf.getvalue())
    return CE


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit("FAILED: %s\n%s%s" % (" ".join(cmd), r.stdout[-2000:], r.stderr[-2000:]))
    return r


# ============================================================ 1. frontend -> shared IR
def frontend(src, top, out):
    """RTL (or a ready generic-gate JSON) -> the SHARED IR: yosys write_json of
    generic gates ($_AND_/$_OR_/$_XOR_/$_NOT_/$_MUX_/$_DFF_P_).  Recipe verbatim from
    nulex/mapper/alu/synth_alu.ys (reproduces the committed alu.json census exactly).
    Also emits the word-level JSON (keeps $add) for the word-level QDI mapper, per
    threeway/run_direct.sh step 1."""
    gen = os.path.join(out, top + ".gates.json")
    word = os.path.join(out, top + ".word.json")
    if src.endswith(".json"):
        shutil.copyfile(src, gen)
        return gen, None
    run(["yosys", "-q", "-p",
         "read_verilog -sv %s; hierarchy -check -top %s; proc; flatten; opt -full; "
         "techmap; opt -full; dfflegalize -cell $_DFF_P_ x; simplemap; opt_clean; "
         "write_json %s" % (src, top, gen)])
    run(["yosys", "-q", "-p",
         "read_verilog %s; hierarchy -top %s; proc; opt -nodffe -nosdff; "
         "write_json %s" % (src, top, word)])
    return gen, word


# ================================================================ 2. analyze + prune
SEQ_TYPES = {"$_DFF_P_", "$_DFF_N_", "$_DFFE_PP_", "$_SDFF_PP0_", "$_SDFF_PP1_"}
MEM_TYPES = ("$mem", "$mem_v2", "$memrd", "$memwr", "$meminit")


def analyze(genjson, wordjson, top):
    m = json.load(open(genjson))["modules"][top]
    cells = m["cells"]
    mix = collections.Counter(c["type"] for c in cells.values()
                              if c["type"] != "$scopeinfo")
    nseq = sum(n for t, n in mix.items() if t in SEQ_TYPES)
    ncomb = sum(n for t, n in mix.items() if t not in SEQ_TYPES)
    nmux = mix.get("$_MUX_", 0)
    a = {"top": top, "genjson": genjson, "mix": dict(mix), "n_comb": ncomb,
         "n_seq": nseq, "mux_pct": 100.0 * nmux / max(1, ncomb)}

    # --- G-A: register CYCLES (pipeline_stages raises on feedback) --------------
    # G-A is "register CYCLES, not registers" (SELECTION-RULE section 1).  The
    # shared-IR recipe runs dfflegalize, which folds every $_DFFE_ enable into a
    # Q->D hold mux, turning every enabled register into a SELF-loop.  A self-hold
    # is state, not a pipeline cycle -- the whole-Vortex census (permodule.json
    # regs_in_cycles, $_DFFE_ preserved) counts the same way.  So: try
    # pipeline_stages() verbatim; if it raises, retry with self-edges dropped and
    # gate only on cycles among DISTINCT registers.
    a["stages"] = None
    a["cycles"] = False
    a["ga_note"] = ""
    if nseq:
        try:
            st = MS.pipeline_stages(cells)      # map_ncl_struct.py:298-350
            a["stages"] = dict(collections.Counter(st.values()))
        except SystemExit:
            st, msg = stages_noself(cells)
            if st is not None:
                a["stages"] = dict(collections.Counter(st.values()))
                a["ga_note"] = ("self-hold edges dropped (dfflegalize DFFE-fold "
                                "artifact); no cycles among distinct registers")
            else:
                a["cycles"] = True
                a["cycle_msg"] = msg

    # --- G-D: SRAM/macro content -------------------------------------------------
    a["mem"] = 0
    if wordjson:
        wm = json.load(open(wordjson))["modules"][top]
        a["mem"] = sum(1 for c in wm["cells"].values()
                       if c["type"].startswith(MEM_TYPES))

    # --- G-C: arbitration / non-determinism (name-token heuristic, labelled) -----
    toks = [top] + list(m["ports"])
    a["arb"] = any(re.search(r"arb|mutex|grant|lock", t, re.I) for t in toks)

    # --- G-B: cone-support census over PO + register-D endpoints -----------------
    # Comb-only blocks with a word-level netlist are censused at WORD level, with
    # $add outputs as cut points -- exactly map_ncl_direct.py's stop set (:447):
    # the adder is expanded as the Fant ripple unit, never as a cone, so an adder
    # chain does not disqualify the word-level direct form.
    wc = cone_census_word(wordjson, top) if (wordjson and nseq == 0) else None
    if wc is not None and wc["word_mappable"] is not None:
        a.update(wc)
        a["gb_basis"] = "word-level ($add cut as Fant adder unit)"
    else:
        a.update(cone_census(m))
        a["word_mappable"] = False
        a["gb_basis"] = "generic-gate netlist"

    # --- G-E: wire dominance (proxy only; abstain-flag) ---------------------------
    a["wire_dominated"] = a["mux_pct"] > 99.0   # Class-4 interconnect shape

    return a


def stages_noself(cells):
    """Register->stage assignment with SELF-dependency edges removed (the
    dfflegalize hold-mux artifact); same dependency walk as
    map_ncl_struct.pipeline_stages().  Returns (stage dict, None) or (None, msg)
    when a cycle among DISTINCT registers remains."""
    drv, reg_of_q, reg_d = {}, {}, {}
    for name, c in cells.items():
        t = c["type"]
        if t == "$_DFF_P_":
            reg_of_q[c["connections"]["Q"][0]] = name
            reg_d[name] = c["connections"]["D"][0]
        elif t != "$scopeinfo":
            for b in c["connections"].get("Y", []):
                if isinstance(b, int):
                    drv[b] = c
    def deps_of(dnet):
        seen, stack, regs = set(), [dnet], set()
        while stack:
            n = stack.pop()
            if not isinstance(n, int):
                continue
            if n in reg_of_q:
                regs.add(reg_of_q[n])
                continue
            if n in seen:
                continue
            seen.add(n)
            c = drv.get(n)
            if c is None:
                continue
            for pin, conns in c["connections"].items():
                if pin != "Y":
                    stack.extend(conns)
        return regs
    deps = {r: deps_of(reg_d[r]) - {r} for r in reg_d}
    stage, state = {}, {}
    order = list(deps)
    for r0 in order:
        st = [(r0, iter(deps[r0]))]
        state.setdefault(r0, 1)
        while st:
            r, it = st[-1]
            nxt = next(it, None)
            if nxt is None:
                stage[r] = 1 + max((stage[x] for x in deps[r]), default=-1)
                state[r] = 2
                st.pop()
                continue
            if state.get(nxt) == 1:
                return None, "register cycle among distinct registers through %s" % nxt
            if state.get(nxt) != 2:
                state[nxt] = 1
                st.append((nxt, iter(deps[nxt])))
    return stage, None


BITOPS = {"$and", "$or", "$xor", "$xnor", "$not", "$_AND_", "$_OR_", "$_XOR_",
          "$_XNOR_", "$_NOT_", "$_NAND_", "$_NOR_", "$_MUX_", "$mux"}


def cone_census_word(wordjson, top):
    """Word-level cone census, mirroring map_ncl_direct.py's front end (:355-401):
    bit-level DAG over the word netlist, cut points = primary inputs + $add outputs
    (+constants).  Returns None-mappable if the netlist holds cell types the
    word-level mapper has no handling for."""
    m = json.load(open(wordjson))["modules"][top]
    node, addout = {}, set()
    bk = MD.bitkey
    for cn, c in m["cells"].items():
        t = c["type"]
        if t == "$scopeinfo":
            continue
        if t == "$add":
            addout.update(bk(y) for y in c["connections"]["Y"])
            continue
        if t not in BITOPS:
            return {"word_mappable": None}       # word route unavailable
        conn = c["connections"]
        for i, y in enumerate(conn["Y"]):
            ins = []
            for p, b in conn.items():
                if p == "Y":
                    continue
                # 1-bit control (e.g. $mux S) fans to every result bit; a narrower
                # operand is zero-extended, matching map_ncl_direct.py:384-388.
                ins.append(bk(b[0] if len(b) == 1 else (b[i] if i < len(b) else "0")))
            node[bk(y)] = ins
    inbits, ends = set(), []
    for pn, p in m["ports"].items():
        for i, b in enumerate(p["bits"]):
            if p["direction"] == "input":
                inbits.add(bk(b))
            else:
                ends.append(bk(b))
    stop = inbits | addout
    n_over, over_roots = 0, []
    for b in ends:
        sup, seen, st = set(), set(), [b]
        while st:
            x = st.pop()
            if x in seen:
                continue
            seen.add(x)
            if x in stop or x not in node:
                if x not in ("0", "1"):
                    sup.add(x)
                continue
            st.extend(node[x])
        if b not in stop and b in node and len(sup) > MD.MAXSUP:
            n_over += 1
            over_roots.append(b)
    mass = set()
    st = list(over_roots)
    seen = set()
    while st:
        x = st.pop()
        if x in seen or x in stop or x not in node:
            continue
        seen.add(x)
        mass.add(x)
        st.extend(node[x])
    return {"word_mappable": n_over == 0, "n_endpoints": len(ends),
            "n_over_maxsup": n_over,
            "pct_endpoints_over": 100.0 * n_over / max(1, len(ends)),
            "pct_regd_over": 0.0,
            "pct_mass_over": 100.0 * len(mass) / max(1, len(node))}


def cone_census(mod):
    """Per-endpoint TRUE cone support (transitive fan-in to PI/regQ/const) on the
    generic-gate netlist; the G-B discriminant.  Support > MAXSUP has no direct
    threshold form (map_ncl_direct.py:81, enforced :483-486)."""
    drv, regq, regd = {}, set(), []
    cells = []
    for cn, c in mod["cells"].items():
        t = c["type"]
        if t == "$scopeinfo":
            continue
        conn = c["connections"]
        if t in SEQ_TYPES:
            regq.update(b for b in conn.get("Q", []) if isinstance(b, int))
            regd.extend(b for b in conn.get("D", []) if isinstance(b, int))
            continue
        ins = [b for p, bs in conn.items() if p != "Y" for b in bs]
        outs = [b for b in conn.get("Y", [])]
        cells.append((cn, ins, outs))
        for b in outs:
            if isinstance(b, int):
                drv[b] = (cn, ins)
    pis = set()
    for p, q in mod["ports"].items():
        if q["direction"] == "input":
            pis.update(b for b in q["bits"] if isinstance(b, int))
    stops = pis | regq
    sup = {}

    def support(net):
        if not isinstance(net, int) or net in stops or net not in drv:
            return frozenset([net]) if (isinstance(net, int) and net in stops) else frozenset()
        st = [net]
        while st:
            n = st[-1]
            if n in sup:
                st.pop()
                continue
            _, ins = drv[n]
            pend = [x for x in ins if isinstance(x, int) and x not in stops
                    and x in drv and x not in sup]
            if pend:
                st.extend(pend)
                continue
            acc = set()
            for x in ins:
                if isinstance(x, int) and x in stops:
                    acc.add(x)
                elif isinstance(x, int) and x in drv:
                    acc |= sup[x]
            sup[n] = frozenset(acc)
            st.pop()
        return sup[net]

    ends = []
    for p, q in mod["ports"].items():
        if q["direction"] == "output":
            ends += [("po", b) for b in q["bits"] if isinstance(b, int)]
    ends += [("regD", b) for b in regd if isinstance(b, int)]
    over_nets, n_over, n_regd_over, n_regd = set(), 0, 0, 0
    for kind, b in ends:
        s = len(support(b))
        if kind == "regD":
            n_regd += 1
        if s > MD.MAXSUP:
            n_over += 1
            over_nets.add(b)
            if kind == "regD":
                n_regd_over += 1
    # cell mass inside over-MAXSUP cones (union of backward cones)
    seen, st = set(), [b for b in over_nets]
    mass = set()
    while st:
        n = st.pop()
        if n in seen or not isinstance(n, int) or n in stops or n not in drv:
            continue
        seen.add(n)
        cn, ins = drv[n]
        mass.add(cn)
        st.extend(ins)
    ncomb = len(cells)
    return {"n_endpoints": len(ends), "n_over_maxsup": n_over,
            "pct_endpoints_over": 100.0 * n_over / max(1, len(ends)),
            "pct_regd_over": 100.0 * n_regd_over / max(1, n_regd) if n_regd else 0.0,
            "pct_mass_over": 100.0 * len(mass) / max(1, ncomb)}


def prune(a):
    """SELECTION-RULE.md section 1 hard gates -> which bindings may be BUILT.
    Gates prune structure; they do not decide the winner."""
    notes = {}
    qdi_ok = True
    if a["cycles"]:
        qdi_ok = False
        notes["QDI"] = ("G-A register CYCLES -> pure 4-phase QDI illegal "
                        "(map_ncl_struct.py:342-343 raises); desync route = "
                        "BD-with-a-local-clock, T1/T2")
    if a["mem"]:
        qdi_ok = False
        notes["QDI"] = notes.get("QDI", "") + " G-D SRAM/macro -> sync interface"
    if a["arb"]:
        notes["ALL"] = "G-C arbitration tokens in names -> sync unconditionally (heuristic)"
    if a["pct_mass_over"] > 10.0:
        notes["QDI-GB"] = ("G-B: %.1f%% of cell mass in cones over MAXSUP=%d "
                           "(%.1f%% of register-D cones over) -> word-level direct-"
                           "threshold has no form; the gate-level TILED variant "
                           "(map_ncl_direct_gl --maxgates 1) is still structurally "
                           "legal and is emitted+scored -- G-B predicts it loses"
                           % (a["pct_mass_over"], MD.MAXSUP, a["pct_regd_over"]))
    if a["wire_dominated"]:
        notes["G-E"] = ("wire-dominance proxy (%.1f%% MUX): models have no basis on "
                        "interconnect -> ABSTAIN, default SYNC" % a["mux_pct"])
    return qdi_ok, notes


# ==================================================================== 3. emission
def emit_sync(a, src_or_gen, top, out, comb_only):
    """SG13G2 sync netlist.  Sequential blocks: the run_synth.sh recipe
    (alu_cmos/run_synth.sh:8-9; reproduces the committed alu.cmos.v byte-identical).
    Combinational blocks: dfflibmap-free abc over the SHARED generic IR (reproduces
    the committed work/sha_slice.cmos.v byte-identical)."""
    v = os.path.join(out, top + ".cmos.v")
    stat = os.path.join(out, top + ".cmos.stat.txt")
    if comb_only:
        if src_or_gen.endswith(".json"):
            front = "read_json %s" % src_or_gen
        else:
            # from RTL: the exact generic+abc route that produced the committed
            # work/sha_slice.cmos.v (byte-identical, so a committed VCD annotates)
            front = ("read_verilog -sv %s; hierarchy -top %s; proc; flatten; "
                     "opt -full; techmap; opt -full; simplemap; opt_clean"
                     % (src_or_gen, top))
        script = ("%s; abc -liberty %s; opt_clean; "
                  "tee -q -o %s stat -liberty %s; write_verilog -noattr %s"
                  % (front, LIB, stat, LIB, v))
    else:
        script = ("read_verilog -sv %s; hierarchy -top %s; synth -top %s -flatten; "
                  "dfflibmap -liberty %s; abc -liberty %s; opt_clean; "
                  "tee -q -o %s stat -liberty %s; write_verilog -noattr %s"
                  % (src_or_gen, top, top, LIB, LIB, stat, LIB, v))
    run(["yosys", "-q", "-p", script])
    txt = open(stat).read()
    cellsm = re.search(r"(\d+)\s+[\d.eE+-]+\s+cells", txt)
    aream = re.search(r"Chip area for .*: ([\d.]+)", txt)
    return {"v": v, "cells": int(cellsm.group(1)) if cellsm else None,
            "area_um2": float(aream.group(1)) if aream else None}


def sta_critpath(v, top, out, has_clk):
    tcl = os.path.join(out, "_sta.tcl")
    open(tcl, "w").write(
        "read_liberty %s\nread_verilog %s\nlink_design %s\n"
        "create_clock -name vclk -period 10%s\n"
        "set_input_delay 0 -clock vclk [all_inputs]\n"
        "set_output_delay 0 -clock vclk [all_outputs]\n"
        "report_checks -path_delay max -group_count 1 -digits 4\n"
        % (LIB, v, top, " [get_ports clk]" if has_clk else ""))
    r = run(["sta", "-no_splash", "-exit", tcl])
    m = re.search(r"([\d.]+)\s+data arrival time", r.stdout)
    return float(m.group(1)) if m else None


def sta_power_vcd(v, top, out, vcd, scope, op_ns):
    tcl = os.path.join(out, "_pwr.tcl")
    open(tcl, "w").write(
        "read_liberty %s\nread_verilog %s\nlink_design %s\n"
        "create_clock -name vclk -period 10\nread_vcd -scope %s %s\n"
        "report_power -digits 6\n" % (LIB, v, top, scope, vcd))
    r = run(["sta", "-no_splash", "-exit", tcl])
    m = re.search(r"^Total\s+\S+\s+\S+\s+\S+\s+([\d.eE+-]+)", r.stdout, re.M)
    if not m:
        return None
    watts = float(m.group(1))
    return watts * op_ns * 1e-9 * 1e15          # fJ per op window


def emit_qdi(a, genjson, wordjson, top, out):
    """Direct-threshold QDI netlists.  Word-level cone mapper when every cone fits
    (comb blocks; run_direct.sh step 2); gate-level tiling with --maxgates 1 (the
    committed campaign variant, byte-identical to alu_direct_cdpo.v) otherwise.
    Returns list of (label, file) plus ring stages for feed-forward registered blocks."""
    outs = {}
    word_ok = (wordjson is not None and a["n_seq"] == 0 and a["mem"] == 0
               and a.get("word_mappable"))
    if word_ok:
        base = os.path.join(out, top + ".qdi_direct.v")
        cd = os.path.join(out, top + ".qdi_direct_cd.v")
        for f, flags in ((base, []), (cd, ["--cd", "tree"])):
            run(["python3", os.path.join(NULEX, "map_ncl_direct.py"), wordjson, top, f,
                 "--target", "verilog", "--cells", "spice",
                 "--census", f + ".census.json"] + flags)
        outs["logic"] = base
        outs["logic_cd"] = cd
        outs["route"] = "word-level (map_ncl_direct.py, cones <= MAXSUP)"
    else:
        cd = os.path.join(out, top + ".qdi_direct_cdpo.v")
        run(["python3", os.path.join(NULEX, "map_ncl_direct_gl.py"), genjson, top, cd,
             "--cells", "spice", "--maxgates", "1", "--cd", "tree", "--cd-scope", "po",
             "--census", cd + ".census.json"])
        outs["logic_cd"] = cd
        outs["route"] = ("gate-level tiling (map_ncl_direct_gl.py --maxgates 1 "
                         "--cd tree --cd-scope po; the committed campaign variant)")
    # ring registers: one 4-phase boundary per pipeline stage, boundary k carries
    # the CUMULATIVE live state sum(W_j, j<=k) -- reproduces the committed
    # regstage152+regstage188 composition for the ALU (alu_async_cost.json).
    outs["rings"] = []
    if a["n_seq"] and not a["cycles"] and a["stages"]:
        widths = []
        acc = 0
        for s in sorted(a["stages"]):
            acc += a["stages"][s]
            widths.append(acc)
        for w in widths:
            f = os.path.join(out, "regstage%d.v" % w)
            open(f, "w").write(gen_regstage(w))
            outs["rings"].append((w, f))
    return outs


def gen_regstage(w):
    """QDI 4-phase registration stage -- byte-identical to the committed
    threeway/alu/regstage188.v / regstage152.v template.
    Per bit: TH22(d.L,ki)->q.L, TH22(d.H,ki)->q.H, TH12(q.L,q.H)->is-DATA;
    balanced TH22 C-element tree -> ko.  3W+(W-1) cells (SELECTION-RULE section 0)."""
    L = ["// GENERATED: QDI 4-phase registration stage, %d dual-rail bits." % w,
         "// Per bit: TH22(d.L, ki) -> q.L, TH22(d.H, ki) -> q.H, TH12(q.L,q.H) -> is-DATA.",
         "// Per stage: a balanced TH22 C-element tree over the is-DATA signals -> ko.",
         "(* blackbox *) module th22(input a, input b, output y); endmodule",
         "(* blackbox *) module th12(input a, input b, output y); endmodule",
         "module regstage%d (input [%d:0] d_L, input [%d:0] d_H, input ki, "
         "output [%d:0] q_L, output [%d:0] q_H, output ko);" % (w, w - 1, w - 1, w - 1, w - 1)]
    u = [0]

    def inst(cell, x, y, o):
        L.append("  %s u%d (.a(%s), .b(%s), .y(%s));" % (cell, u[0], x, y, o))
        u[0] += 1
    cds = []
    for i in range(w):
        inst("th22", "d_L[%d]" % i, "ki", "q_L[%d]" % i)
        inst("th22", "d_H[%d]" % i, "ki", "q_H[%d]" % i)
        L.append("  wire cd%d;" % i)
        inst("th12", "q_L[%d]" % i, "q_H[%d]" % i, "cd%d" % i)
        cds.append("cd%d" % i)
    lvl, k = cds, 0
    while len(lvl) > 1:
        nxt = []
        for j in range(0, len(lvl), 2):
            if j + 1 < len(lvl):
                acc = "acc%d_%d" % (k, j // 2)
                L.append("  wire %s;" % acc)
                inst("th22", lvl[j], lvl[j + 1], acc)
                nxt.append(acc)
            else:
                nxt.append(lvl[j])
        lvl, k = nxt, k + 1
    L.append("  assign ko = %s;" % lvl[0])
    L.append("endmodule")
    return "\n".join(L) + "\n"


def emit_dims(genjson, top, out):
    f = os.path.join(out, top + ".dims.v")
    run(["python3", os.path.join(NULEX, "map_ncl_struct.py"), genjson, top, f,
         "--target", "verilog"])
    # pinned-HIGH inputs are what stop a hysteretic cell ever returning to NULL
    # (the reason the 616-cell ALU DIMS netlist never ran)
    pinned = sum(1 for line in open(f)
                 if re.search(r"th\d+\w* u\d+ \(.*1'b1", line))
    return f, pinned


# ==================================================================== 4. scoring
def cost_th(vfile, top, nv, boundary=(), tie1=(), label=""):
    """Whole-netlist QDI/DIMS cost: compose_alu.run() -- the SAME measured per-arc
    E(C_L) models as compose_async.py, whole-netlist costing (the 4303.7-vs-4385.7
    lesson: never sum separately-costed pieces)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r = CA.run(vfile, top, nv, 2.0, set(boundary), label or vfile, 0.0, set(tie1))
        d, w, p = CA.timing(r)
    tot = r["total"]
    return {"cells": sum(r["ncell"].values()), "census": dict(r["ncell"]),
            "E_fJ": tot[0], "E_lo": tot[1], "E_hi": tot[2],
            "alpha": sum(r["fire"].values()) / sum(r["ncell"].values()),
            "latency_ps": d, "endpoint": w,
            "unmeas_per_op": sum(r["unmeas"].values())}


def ring_cost_incontext(w, qdi_logic_v, top):
    """Ring-stage energy with the q rails carrying their REAL downstream loads in
    the logic cloud (whole-netlist doctrine).  Same measured arcs as compose_alu.E:
    th22.2 / th22.1 / th12.1.  Firing pattern is deterministic: per DATA op exactly
    one of the two q-rail TH22s fires, the TH12 and the whole C-tree fire."""
    caps = CI.pin_caps()
    E22, E22n, E12 = CA.E["th22.2"], CA.E["th22.1"], CA.E["th12.1"]
    cells, ports, _, _ = CA.load(qdi_logic_v, top, set())
    sink = collections.defaultdict(list)
    for t, ins, y in cells:
        for p, n in zip(CA.PINS, ins):
            sink[n].append((t, p))
    qload = {}
    for pn, (bits, d) in ports.items():
        if pn in ("qreg_L", "qreg_H"):
            for i, b in enumerate(bits):
                qload[(pn[-1], i)] = sum(caps.get((st, sp), 0.0)
                                         for st, sp in sink.get(b, []))
    tot = 0.0
    for i in range(w):
        for r in ("L", "H"):
            cl = 2.0 + caps[("th12", "a" if r == "L" else "b")] + qload.get((r, i), 0.0)
            tot += 0.5 * (E22[0] + E22[1] * cl) + 0.5 * E22n[0]
    # completion: TH12 per bit + balanced TH22 tree (all fire every op)
    tree, lvl, k = [], ["cd%d" % i for i in range(w)], 0
    while len(lvl) > 1:
        nxt = []
        for j in range(0, len(lvl), 2):
            if j + 1 < len(lvl):
                acc = "acc%d_%d" % (k, j // 2)
                tree.append((lvl[j], lvl[j + 1], acc))
                nxt.append(acc)
            else:
                nxt.append(lvl[j])
        lvl, k = nxt, k + 1
    root = lvl[0]
    load = collections.defaultdict(float)
    for x, y, o in tree:
        load[x] += caps[("th22", "a")]
        load[y] += caps[("th22", "b")]
    for i in range(w):
        tot += E12[0] + E12[1] * load["cd%d" % i]
    for x, y, o in tree:
        cl = load[o] if o != root else 2.0
        tot += E22[0] + E22[1] * cl
    # forward handshake latency: th22(q) + th12 + ceil(log2 w) th22 tree levels
    D22, D12 = CA.D["th22"], CA.D["th12"]
    lat = (D22[0] + D22[1] * (2.0 + caps[("th12", "a")])
           + D12[0] + D12[1] * caps[("th22", "a")]
           + sum(D22[0] + D22[1] * (load["acc%d_0" % j] if j else 2.0)
                 for j in range(max(1, math.ceil(math.log2(max(2, w)))))))
    return {"cells": 3 * w + (w - 1), "E_fJ": tot, "latency_ps": lat}


def qal_row(a, cmos_v, top, profile, workload, sync_E_op):
    """ANALYSIS-ONLY QAL score: SELECTION-RULE section 3 admission (bank-partition
    DP, max-min bank under span<=4) + the compose_qal_alu.py energy composition
    generalized to this block's SG13G2-mapped netlist."""
    lib, wid = CQ.liberty(), CQ.widths()
    inv_c, inv_wp, inv_wt = (lib["sg13g2_inv_1"]["sumcin"], wid["sg13g2_inv_1"]["wp"],
                             wid["sg13g2_inv_1"]["wtot"])
    c_self = CQ.C_EFF_PER_GATE - 0.5 * CQ.CLOAD_ANCHOR
    # parse the emitted SG13G2 netlist (same structure as CQ.mapped_netlist)
    src = open(cmos_v).read()
    body = src[src.index("module %s" % top):]
    body = body[:body.index("endmodule")]
    insts = {}
    for m in re.finditer(r"^\s*(sg13g2_\w+)\s+(\\?\S+)\s*\((.*?)\);", body, re.M | re.S):
        ct, cn, conns = m.groups()
        pins = {k: v.strip() for k, v in re.findall(r"\.(\w+)\(([^)]*)\)", conns)}
        insts[cn] = (ct, pins)
    sinks = collections.defaultdict(list)
    for cn, (ct, pins) in insts.items():
        for p, net in pins.items():
            if p in ("X", "Y", "Q"):
                continue
            sinks[net].append((ct, p))
    e_wp = e_cin = 0.0
    nmap = 0
    for cn, (ct, pins) in insts.items():
        if "dfrbpq" in ct:
            continue
        nmap += 1
        outn = pins.get("X") or pins.get("Y")
        sk = sinks.get(outn, [])
        cl = sum(lib[st]["cin"].get(sp, 0.0) for st, sp in sk) if sk else 6.0
        e_wp += CQ.E_GATE_SETTLE * (c_self * wid[ct]["wp"] / inv_wp + 0.5 * cl) / CQ.C_EFF_PER_GATE
        e_cin += CQ.E_GATE_SETTLE * (c_self * lib[ct]["sumcin"] / inv_c + 0.5 * cl) / CQ.C_EFF_PER_GATE
    # switch tax band: ideal-PWL-recovered .. plain CMOS buffer (compose_qal_alu (d).1)
    cg_per_um = inv_c / inv_wt
    e_full_gate = (CQ.WSW_TOT * cg_per_um) * CQ.VGH ** 2 / CQ.N_ANCHOR
    sw_lo, sw_hi = nmap * CQ.EGT_HOP / CQ.N_ANCHOR, nmap * e_full_gate
    D = len(profile)
    zcd_lo, zcd_hi = D * CQ.E_ZCD[0], D * CQ.E_ZCD[1]
    logic_lo, logic_hi = min(e_wp, e_cin), max(e_wp, e_cin)
    sub_lo, sub_hi = logic_lo + sw_lo + zcd_lo, logic_hi + sw_hi + zcd_hi
    # registers: DC-powered DFF at the wave boundary -- the only measured option
    # (compose_qal_alu (e)); e_ff = measured seq energy per flop per cycle.
    ce = CE
    dff = a["n_seq"] * (ce.E_SEQ_CYC / ce.N_FF_A) if a["n_seq"] else 0.0
    tot_lo, tot_hi = sub_lo + dff, sub_hi + dff

    # ---- admission: bank-partition DP (max-min bank, contiguous, span<=4) -------
    def dp_maxmin(prof):
        n = len(prof)
        pre = [0]
        for x in prof:
            pre.append(pre[-1] + x)
        dp = [-1.0] * (n + 1)
        dp[0] = float("inf")
        for j in range(1, n + 1):
            best = -1.0
            for i in range(max(0, j - BANK_SPAN), j):
                if dp[i] < 0:
                    continue
                best = max(best, min(dp[i], pre[j] - pre[i]))
            dp[j] = best
        return dp[n]
    minb_full = dp_maxmin(profile)
    # Bush/tail cut: NEVER per-level (the per-level reading misread the ALU twice
    # -- SELECTION-RULE section 3).  The bush is the LONGEST PREFIX whose best
    # contiguous partition still sustains N_min; the excised tail is the control
    # path (on the ALU: the deepest 22 cells, two 2-wide control lanes).
    knee = 0
    for k in range(len(profile), 0, -1):
        if dp_maxmin(profile[:k]) >= NMIN_WORKING:
            knee = k
            break
    bush, tail = profile[:knee], profile[knee:]
    minb_bush = dp_maxmin(bush) if bush else 0.0
    burst = workload.get("burst")
    if not bush or minb_bush < NMIN_WORKING:
        verdict = "EXCLUDED (best min-bank %.0f < N_min working %d even after tail excision)" \
                  % (minb_bush, NMIN_WORKING)
    elif burst is not None and burst < BURST_AMORTIZED:
        verdict = ("EXCLUDED under this workload (burst B=%.1f < %d: fill/drain "
                   "never amortize; per-bank overheads are per-op)"
                   % (burst, BURST_AMORTIZED))
    elif minb_bush <= NMIN_UNDECIDABLE_HI:
        verdict = ("UNDECIDABLE (best min-bank %.0f in the 50-400 band the 10x "
                   "ASSUMED ZCD straddles; simulate the ZCD to decide)" % minb_bush)
    else:
        verdict = "ADMITTED (best min-bank %.0f > %d clears the full ZCD band)" \
                  % (minb_bush, NMIN_UNDECIDABLE_HI)
    return {"maturity": "ANALYSIS-ONLY (T2: no mapper, no cell library, ZCD unsimulated)",
            "E_lo": tot_lo, "E_hi": tot_hi, "E_sub_lo": sub_lo, "E_sub_hi": sub_hi,
            "terms": {"logic_settle": (logic_lo, logic_hi), "switch_tax": (sw_lo, sw_hi),
                      "zcd_x_banks": (zcd_lo, zcd_hi), "dff_dc": dff},
            "nmap": nmap, "banks_per_level": D,
            "triple": (1000.0 / CQ.T_HOP, D * CQ.T_HOP / 1000.0),
            "minb_full": minb_full, "minb_bush": minb_bush,
            "knee_level": knee + 1 if tail else None,
            "bush_cells": sum(bush), "tail_cells": sum(tail),
            "verdict": verdict,
            "hurdle": "needs >=%.0fx vs sync across the FULL ZCD band" % HURDLE["QAL"]}


def levelize(genjson, top, out):
    j = os.path.join(out, top + ".levels.json")
    run(["python3", os.path.join(THREEWAY, "levelize_alu.py"), genjson, top, "--json", j])
    return json.load(open(j))


# =============================================================== 5. workload scoring
def workload_vectors(spec, duty, alpha, alpha_ff, burst, ncyc):
    """--workload module@kernel[,module@kernel...] from permodule.json, or one
    explicit vector."""
    out = []
    if spec:
        pm = json.load(open(PERMODULE))
        NC = {k: v["ncycles"] for k, v in pm["_meta"]["kernels"].items()}
        for w in spec.split(","):
            mod, kern = w.split("@")
            d = pm["modules"][mod]["dynamic"][kern]
            out.append({"name": w, "duty": d["duty2"], "alpha": d["alpha"],
                        "alpha_ff": None, "burst": d.get("work_weighted_burst2"),
                        "busy": d["busy2_cycles"], "ncyc": NC[kern],
                        "src": "MEASURED permodule.json %s@%s" % (mod, kern)})
    if duty is not None:
        nc = int(ncyc or 1000000)
        out.append({"name": "explicit", "duty": duty, "alpha": alpha,
                    "alpha_ff": alpha_ff, "burst": burst,
                    "busy": max(1, int(duty * nc)), "ncyc": nc, "src": "explicit vector"})
    if not out:
        out.append({"name": "duty1-alpha0.05-DEFAULT", "duty": 1.0, "alpha": 0.05,
                    "alpha_ff": None, "burst": None, "busy": 1000000, "ncyc": 1000000,
                    "src": "ASSUMED default (no workload given)"})
    return out


def sync_score(a, wl):
    """COMPOSED sync energy per op under the workload, from compose_energy.compose()
    -- coefficients calibrated on the placed+CTS physical ALU (liberty + per-class
    transistor corrections, physical overhead included)."""
    ce = CE
    r = ce.compose("polysynth", None, static={"comb": a["n_comb"], "seq": a["n_seq"],
                                              "mix": a["mix"]},
                   alpha=wl["alpha"], busy=wl["busy"], nbits=None, ncyc=wl["ncyc"],
                   alpha_ff=wl["alpha_ff"], mix=a["mix"])
    busy = max(1, wl["busy"])
    return {"lib_gated": r["lib_gated"] / busy, "cor_gated": r["cor_gated"] / busy,
            "cor_lo": r["cor_gated_lo"] / busy, "cor_hi": r["cor_gated_hi"] / busy,
            "leak_share": r["leak"] / max(1e-9, r["cor_gated"])}


def qdi_leak_per_op(ncells, wl):
    ce = CE
    t = ce.T_CLK * wl["ncyc"] / max(1, wl["busy"])
    return (ncells * TH_LEAK_BAND_W[0] * t * 1e15,
            ncells * TH_LEAK_BAND_W[1] * t * 1e15)


def bd_row(a, wl, sync, crit_ns):
    """ANALYSIS-ONLY bundled-data: no mapper exists (SELECTION-RULE section 0:
    'bindings/bundled.py' is planned, grep finds nothing).  Composition: the sync
    arm minus the clock TREE (matched delay replaces distribution, registers still
    latch per op) plus the measured delay-line tax band; the controller is ASSUMED
    (unmodeled).  The matched-delay margin has NO named discharger in this flow, so
    BD is refused at tie-break (ii) regardless of score."""
    ce = CE
    busy = max(1, wl["busy"])
    r = ce.compose("bd", None, static={"comb": a["n_comb"], "seq": a["n_seq"],
                                       "mix": a["mix"]},
                   alpha=wl["alpha"], busy=wl["busy"], nbits=None, ncyc=wl["ncyc"],
                   alpha_ff=wl["alpha_ff"], mix=a["mix"])
    base = (r["cor_gated"] - r["tree_g"] * ce.C_TREE) / busy
    return {"maturity": "ANALYSIS-ONLY (T2: no mapper; controller ASSUMED; "
                        "matched-delay margin has no discharger)",
            "E_lo": base * (1 + BD_DELAYLINE[0]), "E_hi": base * (1 + BD_DELAYLINE[1]),
            "latency_ns": crit_ns,
            "note": "sync-minus-clock-tree + delay-line %.1f-%.1f%% [M at real W_eff]; "
                    "hurdle >=%.1fx; refused at tie-break (ii) (assumption discharge)"
                    % (100 * BD_DELAYLINE[0], 100 * BD_DELAYLINE[1], HURDLE["BD"])}


# ===================================================================== 6. the pick
def pick(rows, a, notes, qal, bd, sync_measured):
    """Empirical decider over the scored rows.  Hard gates already pruned; hurdles
    (BD>=1.3x, QDI>=2x, QAL>=3x across the full band) from SELECTION-RULE section 3."""
    sync_E = rows["SYNC"]["E_op"]
    lines = []
    best, why = "SYNC (clock-gated)", None
    if "QDI" in rows and rows["QDI"].get("E_op") is not None:
        q = rows["QDI"]["E_op"]
        if q * HURDLE["QDI"] <= sync_E:
            best = "QDI direct-threshold"
            why = "%.1f fJ/op beats sync %.1f fJ/op by >= the 2x hurdle" % (q, sync_E)
        else:
            lines.append("QDI stays unpicked: %.3g fJ/op vs sync %.3g (needs >=2x)"
                         % (q, sync_E))
    if why is None:
        why = ("lowest emittable energy/op under this workload"
               + ("; measured liberty basis" if sync_measured else "; COMPOSED basis"))
    if qal:
        if qal["verdict"].startswith("ADMITTED") and qal["E_hi"] * HURDLE["QAL"] <= sync_E:
            lines.append("RESEARCH RECOMMENDATION: QAL burst (ANALYSIS-ONLY, T2) -- "
                         "band [%.3g, %.3g] fJ/op beats the 3x hurdle across the FULL "
                         "ZCD band; not buildable (no mapper/ZCD)" % (qal["E_lo"], qal["E_hi"]))
        elif qal["verdict"].startswith("UNDECIDABLE") and qal["E_lo"] * HURDLE["QAL"] <= sync_E:
            lines.append("QAL is UNDECIDABLE here: band [%.3g, %.3g] fJ/op straddles the "
                         "3x hurdle vs sync %.3g AND %s -- decided by: simulate the ZCD; "
                         "measure switch-gate-drive recovery" % (qal["E_lo"], qal["E_hi"],
                                                                 sync_E, qal["verdict"]))
        elif qal["E_lo"] * HURDLE["QAL"] > sync_E:
            lines.append("QAL cannot clear its 3x hurdle even at the lo bound (zero-ZCD, "
                         "recovered switch drive): [%.3g, %.3g] fJ/op vs sync %.3g -- "
                         "the energy decides; the bank-admission verdict is moot here"
                         % (qal["E_lo"], qal["E_hi"], sync_E))
    if bd and bd["E_hi"] * HURDLE["BD"] <= sync_E:
        lines.append("BD would clear its 1.3x hurdle on paper ([%s, %s] vs sync %s) "
                     "but is REFUSED at tie-break (ii): the matched-delay margin has "
                     "no named discharger and no mapper exists -- its real value is "
                     "the current-sense early-out route, not this energy delta"
                     % (fmt_fj(bd["E_lo"]), fmt_fj(bd["E_hi"]), fmt_fj(sync_E)))
    if "G-E" in notes:
        best, why = "ABSTAIN -> default SYNC", notes["G-E"]
    return best, why, lines


# ================================================================== ground truth
GT = {
    "sha_slice": {
        "sync_fJ": 232.0, "sync_ns": 0.9281,     # threeway work/cmos_pwr.tcl (VCD) +
                                                  # cmos_sta.tcl; threeway_gals memory
        "qdi_fJ": 2712.0, "qdi_ns": 2.533,        # 113 cells, direct, no CD
        "qdi_cd_fJ": 4385.7,                      # whole-netlist costing (the lesson)
    },
    "alu_top": {
        "sync_pJ_op": 46.671,                     # placed+CTS liberty, alu_cmos_results.log:34
        "qdi_pJ_op": 523.7,                       # cdpo 479.6 + ring 24.3 + ring 19.7
        "qdi_cells": 25551,
        "qal_band_pJ": (21.0, 146.0),             # compose_qal_alu subtotal-lo .. total-hi
    },
}


def gt_check(name, got, want, tol=0.02):
    err = got / want - 1.0
    ok = abs(err) <= tol
    print("  GT %-28s got %12.4g  want %12.4g  err %+6.2f%%  %s"
          % (name, got, want, 100 * err, "PASS" if ok else "FAIL"))
    return ok


# ========================================================================== main
def fmt_fj(x):
    if x is None:
        return "-"
    return "%.1f fJ" % x if x < 1e4 else "%.2f pJ" % (x / 1e3)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("top")
    ap.add_argument("--workload")
    ap.add_argument("--duty", type=float)
    ap.add_argument("--alpha", type=float)
    ap.add_argument("--alpha-ff", type=float)
    ap.add_argument("--burst", type=float)
    ap.add_argument("--ncyc", type=int)
    ap.add_argument("--out")
    ap.add_argument("--vcd")
    ap.add_argument("--vcd-scope", default="tb/dut")
    ap.add_argument("--op-ns", type=float, default=10.0)
    ap.add_argument("--nv", type=int)
    ap.add_argument("--gt", choices=list(GT))
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--verify", action="store_true",
                    help="run the QDI functional/delay-insensitivity checker")
    ar = ap.parse_args()

    out = ar.out or os.path.join(os.getcwd(), "polysynth_out", ar.top)
    os.makedirs(out, exist_ok=True)
    print("=" * 100)
    print("POLYSYNTH  block=%s  top=%s  out=%s" % (ar.src, ar.top, out))
    print("=" * 100)
    load_CE(out)   # imports compose_energy; its instrument check aborts on drift

    # ---- 1. frontend -> shared IR ------------------------------------------------
    gen, word = frontend(ar.src, ar.top, out)
    a = analyze(gen, word, ar.top)
    print("\n[IR] generic-gate JSON (the shared backend contract): %s" % gen)
    print("     %d comb + %d seq;  mix %s" % (a["n_comb"], a["n_seq"], a["mix"]))

    # ---- 2. prune -----------------------------------------------------------------
    qdi_ok, notes = prune(a)
    print("\n[PRUNE] hard gates (SELECTION-RULE.md section 1 -- pruner, not decider):")
    print("  G-A register cycles : %s%s%s" % (a["cycles"],
          "  stages=%s" % a["stages"] if a["stages"] else "",
          "  [%s]" % a["ga_note"] if a.get("ga_note") else ""))
    print("  G-B cone support    : %d/%d endpoints over MAXSUP=%d (%.1f%% of regD "
          "cones; %.1f%% of cell mass) [basis: %s]"
          % (a["n_over_maxsup"], a["n_endpoints"], MD.MAXSUP,
             a["pct_regd_over"], a["pct_mass_over"], a["gb_basis"]))
    print("  G-C arbitration     : %s (name-token heuristic)" % a["arb"])
    print("  G-D SRAM/macro      : %d (memory_map lowering would cost 43.6x retention "
          "-- SELECTION-RULE section 0)" % a["mem"])
    print("  G-E wire dominance  : %s (mux %.1f%%)" % (a["wire_dominated"], a["mux_pct"]))
    for k, v in notes.items():
        print("  NOTE [%s] %s" % (k, v))

    # ---- 3. emit -------------------------------------------------------------------
    comb_only = (a["n_seq"] == 0)
    sync = emit_sync(a, ar.src, ar.top, out, comb_only)
    crit_ns = sta_critpath(sync["v"], ar.top, out, not comb_only)
    sync_vcd_fJ = None
    if ar.vcd:
        sync_vcd_fJ = sta_power_vcd(sync["v"], ar.top, out, ar.vcd, ar.vcd_scope, ar.op_ns)
    print("\n[EMIT sync] %s  (%s cells, %.1f um2)  crit path %.4f ns [synth-only "
          "liberty; physical adds +40.3%%]"
          % (sync["v"], sync["cells"], sync["area_um2"] or 0.0, crit_ns or 0.0))

    qdi = None
    if qdi_ok and not a["arb"]:
        qdi = emit_qdi(a, gen, word, ar.top, out)
        print("[EMIT QDI]  route: %s" % qdi["route"])
        for w, f in qdi["rings"]:
            print("            ring stage %d bits: %s" % (w, f))
    else:
        print("[EMIT QDI]  NOT EMITTED -- %s" % notes.get("QDI", notes.get("ALL", "")))

    dims_v, dims_pinned = emit_dims(gen, ar.top, out)
    print("[EMIT DIMS] %s  -- INVALID-AS-EMITTED for contrast (%d constant-pinned "
          "hysteretic cells cannot return to NULL; the ALU DIMS netlist never ran)"
          % (dims_v, dims_pinned))

    if ar.verify and qdi:
        v = qdi.get("logic_cd")
        chk = "verify_direct.py" if "qdi_direct" in os.path.basename(v) and comb_only \
              else "verify_alu_direct.py"
        print("[VERIFY] running %s (functional + QDI delay-insensitivity) ..." % chk)
        if chk == "verify_direct.py":
            r = subprocess.run(["python3", os.path.join(THREEWAY, chk), v, ar.top],
                               capture_output=True, text=True)
        else:
            r = subprocess.run(["python3", os.path.join(THREEWAY, chk), v, ar.top,
                                gen, ar.top], capture_output=True, text=True)
        print("  " + (r.stdout.strip().splitlines()[-1] if r.stdout else "no output"))

    # ---- 4. structure-level scores (workload-independent) ---------------------------
    nv_small, nv_big = 4096, 1024
    qdi_cost = ring_costs = qdi_nocd = None
    if qdi:
        nv = ar.nv or (nv_small if a["n_comb"] < 1000 else nv_big)
        qdi_cost = cost_th(qdi["logic_cd"], ar.top, nv, label="QDI direct+CD")
        ring_costs = [ring_cost_incontext(w, qdi["logic_cd"], ar.top)
                      for w, _ in qdi["rings"]]
        qdi_nocd = cost_th(qdi["logic"], ar.top, nv) if "logic" in qdi else None
    dims_cost = cost_th(dims_v, ar.top, ar.nv or (nv_small if a["n_comb"] < 1000 else nv_big),
                        boundary=("ncl_dff",) if a["n_seq"] else (), label="DIMS")

    lv = levelize(gen, ar.top, out)
    profile = lv["profile"]

    # ---- 5. score under each workload ------------------------------------------------
    wls = workload_vectors(ar.workload, ar.duty, ar.alpha, ar.alpha_ff, ar.burst, ar.ncyc)
    results = {"block": ar.top, "analysis": {k: v for k, v in a.items() if k != "genjson"},
               "sync_netlist": sync, "crit_ns": crit_ns, "workloads": {}}

    qdi_total = qdi_cells = None
    if qdi_cost:
        qdi_total = qdi_cost["E_fJ"] + sum(r["E_fJ"] for r in (ring_costs or []))
        qdi_cells = qdi_cost["cells"] + sum(r["cells"] for r in (ring_costs or []))

    for wl in wls:
        print("\n" + "=" * 100)
        print("WORKLOAD %-28s duty=%.4g alpha=%.4g burst=%s   [%s]"
              % (wl["name"], wl["duty"], wl["alpha"],
                 ("%.1f" % wl["burst"]) if wl.get("burst") is not None else "n/a",
                 wl["src"]))
        print("=" * 100)
        ss = sync_score(a, wl)
        sync_E = sync_vcd_fJ if sync_vcd_fJ is not None else ss["cor_gated"]
        rows = {"SYNC": {"E_op": sync_E}}
        qal = qal_row(a, sync["v"], ar.top, profile, wl, sync_E)
        bd = bd_row(a, wl, ss, crit_ns)

        hdr = "%-22s %-38s %14s %26s %16s %s"
        print(hdr % ("variant", "maturity", "E/op", "band / detail", "latency", "cells"))
        print("-" * 130)
        print(hdr % ("SYNC clock-gated", "EMITTABLE T0 (full flow)",
                     fmt_fj(sync_E),
                     ("MEASURED liberty (VCD)" if sync_vcd_fJ is not None else
                      "COMPOSED [%s, %s]" % (fmt_fj(ss["cor_lo"]), fmt_fj(ss["cor_hi"]))),
                     "%.3f ns" % crit_ns if crit_ns else "-",
                     "%s / %.0f um2" % (sync["cells"], sync["area_um2"] or 0)))
        if sync_vcd_fJ is not None:
            print("%22s composed-coefficient column for the same vector: %s "
                  "[COMPOSED; ALU-calibrated coefficients out of regime on very "
                  "small blocks]" % ("", fmt_fj(ss["cor_gated"])))
        if qdi_cost:
            lk = qdi_leak_per_op(qdi_cells, wl)
            qE = qdi_total + 0.5 * (lk[0] + lk[1])
            rows["QDI"] = {"E_op": qE}
            print(hdr % ("QDI direct-thr +CD" + ("+rings" if ring_costs else ""),
                         "EMITTABLE T0 comb / T1 regs (RTZ latch, no scan)",
                         fmt_fj(qE),
                         "COMPOSED-FROM-MEASURED + idle-leak [%s,%s] ASSUMED band"
                         % (fmt_fj(lk[0]), fmt_fj(lk[1])),
                         "%.2f ns fwd%s" % (qdi_cost["latency_ps"] / 1e3,
                                            " +%.1f ns ring" % (max(r["latency_ps"]
                                                for r in ring_costs) / 1e3)
                                            if ring_costs else ""),
                         "%d TH" % qdi_cells))
            if qdi and "logic" in qdi and qdi_nocd:
                print("%22s (no-CD variant: %s @ %.3f ns -- completion detection is "
                      "not optional in QDI; shown for the committed-GT check)"
                      % ("", fmt_fj(qdi_nocd["E_fJ"]), qdi_nocd["latency_ps"] / 1e3))
        print(hdr % ("DIMS (contrast)", "INVALID-AS-EMITTED (%d constant-pinned)" % dims_pinned,
                     fmt_fj(dims_cost["E_fJ"]), "strictly dominated mapping",
                     "%.2f ns" % (dims_cost["latency_ps"] / 1e3),
                     "%d TH" % dims_cost["cells"]))
        print(hdr % ("QAL burst", qal["maturity"][:38],
                     "%s-%s" % (fmt_fj(qal["E_lo"]), fmt_fj(qal["E_hi"])),
                     qal["verdict"][:26],
                     "beat %.0f ps, fill %.2f ns" % (CQ.T_HOP, qal["triple"][1]),
                     "%d banks/lvl" % qal["banks_per_level"]))
        print("%22s terms: logic %s-%s, switch %s-%s [0.7-26 fJ/gate band], ZCD %s-%s "
              "[ASSUMED 30-300 fJ x %d banks], DFF-DC %s"
              % ("", fmt_fj(qal["terms"]["logic_settle"][0]), fmt_fj(qal["terms"]["logic_settle"][1]),
                 fmt_fj(qal["terms"]["switch_tax"][0]), fmt_fj(qal["terms"]["switch_tax"][1]),
                 fmt_fj(qal["terms"]["zcd_x_banks"][0]), fmt_fj(qal["terms"]["zcd_x_banks"][1]),
                 qal["banks_per_level"], fmt_fj(qal["terms"]["dff_dc"])))
        print("%22s admission: min-bank full %.0f / bush %.0f (knee lvl %s, tail %d cells); %s"
              % ("", qal["minb_full"], qal["minb_bush"], qal["knee_level"],
                 qal["tail_cells"], qal["verdict"]))
        print(hdr % ("Bundled-data", bd["maturity"][:38],
                     "%s-%s" % (fmt_fj(bd["E_lo"]), fmt_fj(bd["E_hi"])),
                     "DERIVED/ASSUMED", "%.3f ns + margin[A]" % (crit_ns or 0), "-"))
        print("%22s %s" % ("", bd["note"]))

        best, why, extra = pick(rows, a, notes, qal, bd, sync_vcd_fJ is not None)
        print("-" * 130)
        print("PICK: %s -- %s" % (best, why))
        for e in extra:
            print("      %s" % e)
        results["workloads"][wl["name"]] = {
            "vector": wl, "sync_E_op_fJ": sync_E, "sync_composed": ss,
            "qdi_E_op_fJ": rows.get("QDI", {}).get("E_op"),
            "qal": {k: v for k, v in qal.items() if k != "terms"},
            "bd": bd, "pick": best, "pick_reason": why}

    if len(wls) > 1:
        picks = [results["workloads"][w["name"]]["pick"] for w in wls]
        if len(set(picks)) == 1:
            print("\nRED-FLAG CHECK (a pick that never changes with the workload): the pick "
                  "is '%s' under all %d vectors. Verified real, not a modeling convenience:"
                  % (picks[0], len(picks)))
            print("  the emittable alternatives sit a structural factor away (QDI %.1fx sync"
                  " at best) while the workload moves the sync baseline %.3g-%.3g fJ/op and"
                  " the QAL verdict between EXCLUDED/UNDECIDABLE."
                  % ((min(r["qdi_E_op_fJ"] / r["sync_E_op_fJ"]
                          for r in results["workloads"].values() if r["qdi_E_op_fJ"])
                      if qdi_cost else float("nan")),
                     min(r["sync_E_op_fJ"] for r in results["workloads"].values()),
                     max(r["sync_E_op_fJ"] for r in results["workloads"].values())))

    # ---- 6. ground truth ----------------------------------------------------------
    if ar.gt:
        g = GT[ar.gt]
        print("\n" + "=" * 100)
        print("GROUND-TRUTH REPRODUCTION (%s; committed values from the three-way "
              "campaign)" % ar.gt)
        print("=" * 100)
        ok = True
        if ar.gt == "sha_slice":
            ok &= gt_check("sync 232 fJ/op (liberty+VCD)", sync_vcd_fJ, g["sync_fJ"])
            ok &= gt_check("sync crit path 0.9281 ns", crit_ns, g["sync_ns"])
            ok &= gt_check("QDI direct 2712 fJ", qdi_nocd["E_fJ"], g["qdi_fJ"])
            ok &= gt_check("QDI direct 2.533 ns", qdi_nocd["latency_ps"] / 1e3, g["qdi_ns"])
            ok &= gt_check("QDI direct+CD 4385.7 fJ", qdi_cost["E_fJ"], g["qdi_cd_fJ"])
        else:
            ok &= gt_check("sync 46.671 pJ/op (IMPORT SELF-TEST)", CE.pj_op, g["sync_pJ_op"])
            print("    (CAUTION: this line tests the imported compose_energy instrument "
                  "against its OWN stored data -- it would PASS for any input block. "
                  "It guards against instrument drift only; it is NOT a check of this "
                  "run's emission. The run-specific alu checks are the QDI cells/energy "
                  "lines below.)")
            ok &= gt_check("QDI+CD+rings 523.7 pJ/op", qdi_total / 1e3, g["qdi_pJ_op"])
            ok &= gt_check("QDI cells 25551", float(qdi_cells), float(g["qdi_cells"]), 0.001)
            lo, hi = GT["alu_top"]["qal_band_pJ"]
            qa = results["workloads"][wls[0]["name"]]["qal"]
            print("  GT QAL band ~%g-%g pJ: mine subtotal-lo %.1f .. total-hi %.1f pJ "
                  "(band comparison, no strict tolerance -- ANALYSIS-ONLY row)"
                  % (lo, hi, qa["E_sub_lo"] / 1e3, qa["E_hi"] / 1e3))
        print("GROUND TRUTH: %s" % ("ALL PASS" if ok else "*** FAIL ***"))
        results["gt_pass"] = bool(ok)

    if ar.json_out:
        json.dump(results, open(ar.json_out, "w"), indent=1, default=str)
        print("\nwrote %s" % ar.json_out)
    return 0 if results.get("gt_pass", True) else 1


if __name__ == "__main__":
    sys.exit(main())
