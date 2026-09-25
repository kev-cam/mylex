#!/usr/bin/env python3
"""nulex map_ncl_direct — DIRECT-THRESHOLD technology mapper for dual-rail QDI.

WHY THIS EXISTS.  map_ncl_struct.py decomposes to 2-input gates FIRST and then
stamps a fixed DIMS template on every one of them (MIN4 at map_ncl_struct.py:36-41
= 4x TH22 minterms per 2-input gate, COLLECT at :64 = th12/th13/th14 rail
collectors).  That throws away the NATURAL threshold form of the function: a
3-input majority, which IS one TH23 per rail, comes out as three 2-input gates =
12 TH22 + 3 collectors.  This mapper maps each logic CONE directly onto threshold
cells instead.

ALGORITHM (per output-rail cone, support n <= MAXSUP):
  1. NATURAL THRESHOLD.  Search integer weights w_i and threshold T with
     f(x) == [sum w_i*x_i >= T].  If found, the t-rail is one TH(w,T) cell over
     the inputs' t-rails and the f-rail is one TH(w, W-T+1) cell over the f-rails
     (W = sum w).  1 cell per rail.  (Proof for the f-rail: ~f(x)=1 iff
     sum w_i x_i <= T-1 iff sum w_i (1-x_i) >= W-T+1.)
     A bare threshold cell is NOT input-complete: it fires as soon as ANY
     weight-sufficient subset arrives.  COMPLETENESS UPGRADE for an input k:
        w_k -> 2*w_k on x_k.t, append x_k.f with weight w_k, T -> T + w_k.
     (x_k=1 contributes 2w_k, x_k=0 contributes w_k, x_k=NULL contributes 0 and
     the remaining W-w_k can no longer reach T+w_k when W < T+2*w_k.)
     e.g. majority (1,1,1)/T=2 upgraded on c -> (2,1,1,1)/T=3 = TH34W2(c.t,a.t,b.t,c.f).
  2. COVER (input-complete by construction).  Otherwise take a minimum
     prime-implicant cover of the rail function.  Each cube with k literals and m
     don't-care inputs becomes ONE cell TH(k+m of k+2m) whose inputs are the
     literals' rails plus BOTH rails of every don't-care input -- in DATA exactly
     one rail of a don't-care is high, so it contributes exactly m, and the cube
     cannot fire until every support input is DATA.  If k+2m > 4 (no such library
     cell) the don't-cares are replaced by shared presence signals TH12(x.t,x.f)
     and the cube becomes a TH(k+m,k+m) C-element.  The cubes are OR-ed by a
     threshold-1 collector (th12/th13/th14, tree'd beyond 4).
     e.g. Ch = e?f:g  ->  Ch.t = TH12( TH34(e.t,f.t,g.t,g.f), TH34(e.f,g.t,f.t,f.f) ).
  3. DIMS fallback (the map_ncl_struct template) if the cone is too wide.

  $add is not cone-mappable (the carry chain makes sum[i]'s support 2(i+1) bits),
  so it is expanded as the FANT ripple full adder -- cout=TH23, sum=TH34W2 --
  exactly the form proven in lib/ncl_gates.vhd:197-200 (ncl_add4_struct).
  Constant carry-in rails are folded: a constant-1 input is ALWAYS folded away
  (it would pin a hysteretic cell and stop it ever returning to NULL); a
  constant-0 input is folded only when the reduced cell exists, else tied to VSS.

INPUT-COMPLETENESS PROOF.  emit + check_completeness() computes, for every rail,
the exact set of primary inputs that MUST be DATA before that rail can assert
(intersection over the FEASIBLE minimal asserting subsets of each gate; a subset
is infeasible if it needs both rails of one input).  A block is input-complete
when the union over outputs of (requirements of o.t) INTERSECT (requirements of
o.f) covers every primary input -- that is exactly the condition under which
completion detection over all outputs cannot fire before all inputs are DATA.

Usage:
  map_ncl_direct.py <netlist.json> <top> <out.v|out.vhd>
      [--target verilog|vhdl] [--bind comb|qdi]
      [--cells spice|full]        # spice = only cells with an SG13G2 subckt
      [--cd none|chain|tree]      # completion detector over the outputs
      [--census out.json] [--no-repair]
"""
import itertools
import json
import sys
from collections import OrderedDict

# ---------------------------------------------------------------- cell library
# (sorted weight tuple, threshold) -> cell name.  Weight-2 input is port `a`.
CELLMAP = {
    ((1, 1), 1): "th12", ((1, 1), 2): "th22",
    ((1, 1, 1), 1): "th13", ((1, 1, 1), 2): "th23", ((1, 1, 1), 3): "th33",
    ((1, 1, 1, 1), 1): "th14", ((1, 1, 1, 1), 2): "th24",
    ((1, 1, 1, 1), 3): "th34", ((1, 1, 1, 1), 4): "th44",
    ((2, 1, 1), 2): "th23w2",
    ((2, 1, 1, 1), 3): "th34w2",
}
# cells that have a transistor-level SG13G2 subckt on disk:
#   ldx/asic/cells/th22.sp            th22
#   ldx/asic/cells/th_gates.sp        th12 th23 th33 th34w2
#   nulex/lib/th_cells_sg13g2.sp      th13 th14
SPICE_CELLS = {"th12", "th13", "th14", "th22", "th23", "th33", "th34w2"}
ALL_CELLS = set(CELLMAP.values())
TH_PORTS = {"th12": 2, "th13": 3, "th14": 4, "th22": 2, "th23": 3, "th33": 3,
            "th24": 4, "th34": 4, "th44": 4, "th23w2": 3, "th34w2": 4}
MAXSUP = 4          # cone support above this -> DIMS fallback
MAXW = 3            # weight search bound
NEVER = object()    # requirement-analysis sentinel: "this net can never assert"


def cell_for(weights, thr, allowed):
    """(weights list, threshold) -> (cellname, permutation) or None.
    Returns the permutation that orders inputs to match the cell's port order
    (descending weight; weight-2 input first)."""
    order = sorted(range(len(weights)), key=lambda i: -weights[i])
    key = (tuple(sorted(weights, reverse=True)), thr)
    c = CELLMAP.get(key)
    if c is None or c not in allowed:
        return None
    return c, order


# ------------------------------------------------------------ threshold search
def find_threshold(tt, n):
    """tt: dict {tuple(x) -> 0/1}.  Return (weights, T) or None."""
    best = None
    for w in itertools.product(range(1, MAXW + 1), repeat=n):
        W = sum(w)
        for T in range(1, W + 1):
            if all((sum(wi * xi for wi, xi in zip(w, x)) >= T) == bool(v)
                   for x, v in tt.items()):
                cand = (max(w), W, list(w), T)
                if best is None or cand[:2] < best[:2]:
                    best = cand
        if best and best[0] == 1:
            break
    return (best[2], best[3]) if best else None


# ------------------------------------------------------------- prime implicants
def prime_implicants(onset, n):
    """onset: set of int minterms.  Returns list of cubes (mask, val):
    bit in mask=1 -> literal fixed to val's bit."""
    cubes = {(( 1 << n) - 1, m) for m in onset}
    primes = set()
    while cubes:
        used = set()
        nxt = set()
        for (m1, v1), (m2, v2) in itertools.combinations(sorted(cubes), 2):
            if m1 != m2:
                continue
            d = v1 ^ v2
            if d and (d & (d - 1)) == 0:      # differ in exactly one bit
                nxt.add((m1 & ~d, v1 & ~d))
                used.add((m1, v1)); used.add((m2, v2))
        primes |= (cubes - used)
        cubes = nxt
    return sorted(primes)


def covers(cube, m):
    mask, val = cube
    return (m & mask) == (val & mask)


def min_cover(onset, n):
    """Exact minimum prime-implicant cover (n<=4 so brute force is fine)."""
    if not onset:
        return []
    pis = prime_implicants(onset, n)
    for k in range(1, len(pis) + 1):
        for sel in itertools.combinations(pis, k):
            if all(any(covers(c, m) for c in sel) for m in onset):
                return list(sel)
    return pis


# ==================================================================== the mapper
class Mapper(object):
    def __init__(self, allowed, bind="comb"):
        self.allowed = allowed
        self.cells = []            # (celltype, [in rail nets], out rail net)
        self.aliases = []          # (lhs, rhs) pure wiring
        self.wires = []            # internal net names to declare
        self.n = 0
        self.consts = {"0": "1'b0", "1": "1'b1"}

    # -- net helpers -------------------------------------------------------
    def new(self, pfx="w"):
        self.n += 1
        nm = "%s%d" % (pfx, self.n)
        self.wires.append(nm)
        return nm

    def emit(self, weights, thr, ins, out=None):
        """Emit one threshold gate.  ins = list of rail net names or the strings
        '0'/'1' for constants.  Folds constants.  Returns the output net name."""
        w, xs = list(weights), list(ins)
        # constant-1 MUST be folded: a pinned-high input stops a hysteretic cell
        # from ever returning to NULL.
        keep_w, keep_x = [], []
        for wi, xi in zip(w, xs):
            if xi == "1":
                thr -= wi
            elif xi == "0":
                keep_w.append((wi, xi))
            else:
                keep_w.append((wi, xi)); keep_x.append(xi)
        if thr <= 0:
            if out is not None:
                self.aliases.append((out, "1"))
                return out
            return "1"
        w2 = [a for a, _ in keep_w]; x2 = [b for _, b in keep_w]
        if sum(w2) < thr:
            if out is not None:
                self.aliases.append((out, "0"))
                return out
            return "0"
        r = cell_for(w2, thr, self.allowed)
        if r is None:
            # try dropping constant-0 inputs (they can only be tied to VSS)
            w3 = [a for a, b in keep_w if b != "0"]
            x3 = [b for _, b in keep_w if b != "0"]
            if len(w3) != len(w2) and sum(w3) >= thr:
                r = cell_for(w3, thr, self.allowed)
                if r is not None:
                    w2, x2 = w3, x3
        if r is None:
            return self.emit_decomposed(w2, thr, x2, out)
        cell, order = r
        if out is None:
            out = self.new()
        self.cells.append((cell, [x2[i] for i in order], out))
        return out

    def emit_decomposed(self, w, thr, xs, out=None):
        """No single library cell: Shannon-expand on the largest weight.
        f = [sum w x >= T] = x_k & [rest >= T-w_k]  OR  [rest >= T]."""
        k = max(range(len(w)), key=lambda i: w[i])
        rw = w[:k] + w[k + 1:]
        rx = xs[:k] + xs[k + 1:]
        hi = self.emit(rw, thr - w[k], rx) if thr - w[k] > 0 else "1"
        lo = self.emit(rw, thr, rx) if sum(rw) >= thr else "0"
        both = self.emit([1, 1], 2, [xs[k], hi]) if hi != "1" else xs[k]
        if lo == "0":
            if out is not None:
                self.aliases.append((out, both)); return out
            return both
        return self.emit([1, 1], 1, [both, lo], out)

    def collect(self, terms, out=None):
        """threshold-1 collector over `terms` (tree'd beyond arity 4)."""
        terms = [t for t in terms if t != "0"]
        if not terms:
            return "0"
        if len(terms) == 1:
            if out is not None:
                self.aliases.append((out, terms[0])); return out
            return terms[0]
        while len(terms) > 4:
            nxt = []
            for i in range(0, len(terms), 4):
                grp = terms[i:i + 4]
                nxt.append(self.emit([1] * len(grp), 1, grp) if len(grp) > 1 else grp[0])
            terms = nxt
        return self.emit([1] * len(terms), 1, terms, out)

    # -- cone mapping ------------------------------------------------------
    def map_cone(self, tt_fn, sup, rails, out_t, out_f, complete_on=()):
        """tt_fn: f(tuple of 0/1 over sup) -> 0/1.  sup: list of support ids.
        rails: {sup_id: (t_net, f_net)}.  complete_on: sup ids to force-complete.
        Returns dict with the style used."""
        n = len(sup)
        tt = {}
        for x in itertools.product((0, 1), repeat=n):
            tt[x] = tt_fn(x)
        # index minterms so bit j of the index is sup[j]
        idx_on = set()
        for x, v in tt.items():
            if v:
                idx_on.add(sum(xi << j for j, xi in enumerate(x)))
        if not idx_on:
            self.aliases.append((out_t, "0")); self.aliases.append((out_f, "1"))
            return {"style": "const0"}
        if len(idx_on) == 1 << n:
            self.aliases.append((out_t, "1")); self.aliases.append((out_f, "0"))
            return {"style": "const1"}

        # --- 1. natural threshold ---
        th = find_threshold(tt, n)
        if th:
            w, T = th
            W = sum(w)
            wt, Tt, inst = list(w), T, [rails[s][0] for s in sup]
            wf, Tf, insf = list(w), W - T + 1, [rails[s][1] for s in sup]
            ok = True
            for k in complete_on:
                j = sup.index(k)
                # blocking condition (x_k NULL leaves only W-w_k of weight):
                #   W - w_k < T' - ... i.e. W < T + 2*w_k, on BOTH rails.
                if (len(wt) + 1 > 4 or W >= T + 2 * w[j]
                        or W >= (W - T + 1) + 2 * w[j]):
                    ok = False; break
                wt = wt[:j] + [2 * w[j]] + wt[j + 1:] + [w[j]]
                inst = inst + [rails[k][1]]
                Tt += w[j]
                wf = wf[:j] + [2 * w[j]] + wf[j + 1:] + [w[j]]
                insf = insf + [rails[k][0]]
                Tf += w[j]
            if ok and cell_for(wt, Tt, self.allowed) and cell_for(wf, Tf, self.allowed):
                self.emit(wt, Tt, inst, out_t)
                self.emit(wf, Tf, insf, out_f)
                return {"style": "threshold", "w": w, "T": T,
                        "complete_on": list(complete_on)}

        # --- 2. cover (input-complete by construction) ---
        res = {"style": "cover"}
        pres = {}

        def presence(s):
            if s not in pres:
                pres[s] = self.emit([1, 1], 1, [rails[s][0], rails[s][1]])
            return pres[s]

        for rail, on in (("t", idx_on),
                         ("f", set(range(1 << n)) - idx_on)):
            cov = min_cover(on, n)
            terms = []
            for mask, val in cov:
                lit, dc = [], []
                for j, s in enumerate(sup):
                    if mask >> j & 1:
                        lit.append(rails[s][0] if (val >> j & 1) else rails[s][1])
                    else:
                        dc.append(s)
                k, m = len(lit), len(dc)
                if k + 2 * m <= 4 and cell_for([1] * (k + 2 * m), k + m, self.allowed):
                    ins = lit + [r for s in dc for r in rails[s]]
                    terms.append(self.emit([1] * len(ins), k + m, ins))
                else:
                    ins = lit + [presence(s) for s in dc]
                    terms.append(self.emit([1] * len(ins), len(ins), ins))
            self.collect(terms, out_t if rail == "t" else out_f)
            res["cover_" + rail] = len(cov)
        return res


# ==================================================================== front end
def bitkey(b):
    return b if isinstance(b, int) else str(b)


def main():
    argv = sys.argv[1:]

    def opt(name, dflt):
        return argv[argv.index(name) + 1] if name in argv else dflt
    target = opt("--target", "verilog")
    bind = opt("--bind", "comb")
    cellset = opt("--cells", "spice")
    cd = opt("--cd", "none")
    census_out = opt("--census", None)
    flags = ("--target", "--bind", "--cells", "--cd", "--census")
    bare = ("--no-repair",)      # diagnostic: skip the completeness upgrade pass
    pos = [a for i, a in enumerate(argv)
           if a not in flags and a not in bare
           and (i == 0 or argv[i - 1] not in flags)]
    if len(pos) != 3:
        sys.exit(__doc__)
    jpath, top, out = pos
    allowed = SPICE_CELLS if cellset == "spice" else ALL_CELLS

    d = json.load(open(jpath))
    if top not in d["modules"]:
        sys.exit("top '%s' not in %s" % (top, list(d["modules"])))
    m = d["modules"][top]
    ports, cells = m["ports"], m["cells"]

    # --- bit-level DAG over the word-level netlist ---
    node = {}            # bit -> ('op', op, [bits]) ; absent = cut point
    adders = []          # (A bits, B bits, Y bits)
    BITOPS = {"$and": "and", "$or": "or", "$xor": "xor", "$xnor": "xnor",
              "$not": "not", "$_AND_": "and", "$_OR_": "or", "$_XOR_": "xor",
              "$_XNOR_": "xnor", "$_NOT_": "not", "$_NAND_": "nand",
              "$_NOR_": "nor", "$_MUX_": "mux", "$mux": "mux"}
    for cn, c in cells.items():
        t = c["type"]
        if t == "$scopeinfo":
            continue
        if t == "$add":
            conn = c["connections"]
            adders.append((conn["A"], conn["B"], conn["Y"]))
            continue
        if t not in BITOPS:
            sys.exit("unhandled cell type %s (%s)" % (t, cn))
        op = BITOPS[t]
        conn = c["connections"]
        Y = conn["Y"]
        if op == "not":
            A = conn["A"]
            for i, y in enumerate(Y):
                node[bitkey(y)] = ("not", [bitkey(A[i])])
        elif op == "mux":
            A, B, S = conn["A"], conn["B"], conn["S"]
            for i, y in enumerate(Y):
                node[bitkey(y)] = ("mux", [bitkey(S[0]), bitkey(A[i]), bitkey(B[i])])
        else:
            A, B = conn["A"], conn["B"]
            for i, y in enumerate(Y):
                a = A[i] if i < len(A) else "0"
                b = B[i] if i < len(B) else "0"
                node[bitkey(y)] = (op, [bitkey(a), bitkey(b)])

    # cut points = primary inputs, constants, adder outputs
    inbits = OrderedDict()     # bit -> (portname, idx)
    outbits = []               # (portname, idx, bit)
    for pn, p in ports.items():
        for i, b in enumerate(p["bits"]):
            if p["direction"] == "input":
                inbits[bitkey(b)] = (pn, i)
            else:
                outbits.append((pn, i, bitkey(b)))
    addout = {}
    for ai, (A, B, Y) in enumerate(adders):
        for i, y in enumerate(Y):
            addout[bitkey(y)] = (ai, i)

    # --- cone helpers -----------------------------------------------------
    def cone(b, stop):
        """support list (ordered) of bit b, cutting at `stop`."""
        sup, seen, stack = [], set(), [b]
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            if x in stop or x not in node:
                if x not in ("0", "1") and x not in sup:
                    sup.append(x)
                continue
            stack.extend(node[x][1])
        return sup

    def ev(b, env):
        if b == "0":
            return 0
        if b == "1":
            return 1
        if b in env:
            return env[b]
        op, ins = node[b]
        v = [ev(x, env) for x in ins]
        if op == "and":
            return v[0] & v[1]
        if op == "or":
            return v[0] | v[1]
        if op == "xor":
            return v[0] ^ v[1]
        if op == "xnor":
            return 1 - (v[0] ^ v[1])
        if op == "nand":
            return 1 - (v[0] & v[1])
        if op == "nor":
            return 1 - (v[0] | v[1])
        if op == "not":
            return 1 - v[0]
        if op == "mux":
            return v[2] if v[0] else v[1]
        raise Exception("op " + op)

    stop = set(inbits) | set(addout)

    def build(force):
        """Map the whole block.  `force` maps an output bit -> list of support
        inputs whose presence must be forced (the completeness upgrade).
        Returns (Mapper, rails, cone_report)."""
        mp = Mapper(allowed, bind)
        rails = {}
        for b, (pn, i) in inbits.items():
            rails[b] = (railname(pn, i, ports[pn], "L", target),
                        railname(pn, i, ports[pn], "H", target))
        rails["0"] = ("0", "1")      # DATA0 = (L=0, H=1)
        rails["1"] = ("1", "0")
        # FANT ripple full adder (the form proven in lib/ncl_gates.vhd:197-200)
        for ai, (A, B, Y) in enumerate(adders):
            cint, cinf = "0", "1"                   # carry-in = DATA0
            for i in range(len(Y)):
                at, af = rails[bitkey(A[i])]
                bt, bf = rails[bitkey(B[i])]
                coutt = mp.emit([1, 1, 1], 2, [at, bt, cint])       # th23 majority
                coutf = mp.emit([1, 1, 1], 2, [af, bf, cinf])
                st = mp.new(); sf = mp.new()
                mp.emit([2, 1, 1, 1], 3, [coutf, at, bt, cint], st)  # th34w2
                mp.emit([2, 1, 1, 1], 3, [coutt, af, bf, cinf], sf)
                rails[bitkey(Y[i])] = (st, sf)
                cint, cinf = coutt, coutf
        rep = []
        for pn, i, b in outbits:
            ot = railname(pn, i, ports[pn], "L", target)
            of = railname(pn, i, ports[pn], "H", target)
            if b in rails:                   # adder output / straight input feed
                mp.aliases.append((ot, rails[b][0]))
                mp.aliases.append((of, rails[b][1]))
                rep.append((pn, i, "wire", 0, {}))
                continue
            sup = cone(b, stop)
            if len(sup) > MAXSUP:
                sys.exit("cone %s[%d] support %d > %d: no direct form "
                         "(use map_ncl_struct.py DIMS for this cone)"
                         % (pn, i, len(sup), MAXSUP))
            r = mp.map_cone(lambda x, b=b, sup=sup: ev(b, dict(zip(sup, x))),
                            sup, rails, ot, of,
                            complete_on=[s for s in force.get(b, ()) if s in sup])
            rep.append((pn, i, r["style"], len(sup), r))
            rails[b] = (ot, of)
        return mp, rails, rep

    # pass 1: no forced completeness; pass 2: force whatever came out uncovered
    mp, rails, cone_report = build({})
    req = check_completeness(mp, rails, inbits, ports, outbits, target)
    missing = [b for b in inbits if b not in req]
    repaired = []
    if missing and "--no-repair" not in argv:
        force = {}
        for pn, i, b in outbits:
            if b in addout:
                continue
            need = [s for s in cone(b, stop) if s in missing]
            if need:
                force[b] = need
                repaired.append((pn, i, need, None))
        mp, rails, cone_report = build(force)
        req = check_completeness(mp, rails, inbits, ports, outbits, target)
        missing = [b for b in inbits if b not in req]
        sty = {(p, i): s for p, i, s, _, _ in cone_report}
        repaired = [(p, i, nd, sty.get((p, i), "?")) for p, i, nd, _ in repaired]

    # --- completion detector ---
    cd_cells = 0
    cd_depth = 0
    cd_nets = []
    if cd != "none":
        per = []
        for pn, i, b in outbits:
            ot = railname(pn, i, ports[pn], "L", target)
            of = railname(pn, i, ports[pn], "H", target)
            per.append(mp.emit([1, 1], 1, [ot, of]))        # th12 is-DATA
        base = len(mp.cells)
        if cd == "chain":
            acc = per[0]
            for x in per[1:]:
                acc = mp.emit([1, 1], 2, [acc, x])
            cd_depth = len(per)                              # th12 + (N-1) th22
        else:                                                # balanced C tree
            lvl = per
            cd_depth = 1
            while len(lvl) > 1:
                nxt = []
                for j in range(0, len(lvl), 2):
                    nxt.append(mp.emit([1, 1], 2, lvl[j:j + 2])
                               if len(lvl[j:j + 2]) == 2 else lvl[j])
                lvl = nxt; cd_depth += 1
            acc = lvl[0]
        mp.aliases.append(("done", acc))
        cd_cells = len(mp.cells) - base + len(per)
        cd_nets = ["done"]

    # ---- census + emit ----
    census = {}
    for c, _, _ in mp.cells:
        census[c] = census.get(c, 0) + 1
    total = sum(census.values())

    text = (emit_verilog if target == "verilog" else emit_vhdl)(
        top, ports, mp, cd_nets, bind)
    open(out, "w").write(text)

    info = {"top": top, "cells": census, "total": total,
            "cellset": cellset, "cd": cd,
            "cd_cells": cd_cells, "cd_levels": cd_depth,
            "input_complete": not missing,
            "uncovered_inputs": ["%s[%d]" % inbits[b] for b in missing],
            "cones": [{"port": p, "bit": i, "style": s, "support": n}
                      for p, i, s, n, _ in cone_report],
            "repaired": [{"port": p, "bit": i, "forced": ["%s[%d]" % inbits[x] for x in nd],
                          "style": s} for p, i, nd, s in repaired]}
    if census_out:
        json.dump(info, open(census_out, "w"), indent=1)
    print("wrote %s (target=%s cells=%s cd=%s)" % (out, target, cellset, cd))
    print("  CELL CENSUS: %s   TOTAL=%d" % (
        ", ".join("%s=%d" % kv for kv in sorted(census.items())), total))
    if cd != "none":
        print("  completion detector: %d cells, %d levels (%s)" % (cd_cells, cd_depth, cd))
    print("  input-complete: %s%s" % (
        not missing, "" if not missing else
        "  UNCOVERED: " + ", ".join("%s[%d]" % inbits[b] for b in missing)))
    for p, i, nd, s in repaired:
        print("  completeness-upgraded %s[%d] on %s -> %s"
              % (p, i, ",".join("%s[%d]" % inbits[x] for x in nd), s))


# ------------------------------------------------- input-completeness analysis
CUBE_CAP = 20000


def minimalize(cubes):
    out = []
    for c in sorted(cubes, key=len):
        if not any(o <= c for o in out):
            out.append(c)
    return set(out)


def check_completeness(mp, rails, inbits, ports, outbits, target, detail=None):
    """EXACT structural assertion analysis.  For every net compute A(net) = the
    set of MINIMAL cubes over primary-input RAIL literals that make it assert
    (a rail asserts iff some cube is fully asserted).  Then primary input x is
    REQUIRED by a net iff every cube of that net mentions x on some rail -- i.e.
    the net cannot go high before x is DATA.  An output is DATA when either rail
    is high, so the output requires req(o.t) INTERSECT req(o.f); the completion
    detector waits for all outputs, so the block requirement is the UNION of
    those over the outputs.  Returns that set of primary input bits.

    The intersection-of-requirement-sets shortcut is NOT exact -- it loses the
    correlation between a gate input and its own fanin (e.g. th34w2(coutf,a.t,
    b.t,cin) where coutf = a.f OR b.f: the subset {coutf, a.t} forces a.f away
    and so really needs b.f).  Cubes keep that."""
    A = {}
    for b in inbits:
        t, f = rails[b]
        A[t] = {frozenset([(b, 't')])}
        A[f] = {frozenset([(b, 'f')])}
    A["0"] = set()                      # VSS: never asserts
    A["1"] = {frozenset()}              # VDD: asserts with no requirement
    alias = {}
    for lhs, rhs in mp.aliases:
        alias[lhs] = rhs

    def get(x):
        seen = set()
        while x not in A and x in alias and x not in seen:
            seen.add(x); x = alias[x]
        return A.get(x)

    INV = {}
    for (w, T), c in CELLMAP.items():
        INV[c] = (list(w), T)
    for _ in range(4):                  # emission order is topological; iterate anyway
        stable = True
        for cell, ins, out in mp.cells:
            w, T = INV[cell]
            rs = [get(x) for x in ins]
            if any(r is None for r in rs):
                stable = False
                continue
            acc = set()
            n = len(ins)
            for k in range(1, n + 1):
                for S in itertools.combinations(range(n), k):
                    if sum(w[j] for j in S) < T:
                        continue
                    if any(sum(w[j] for j in S if j != d) >= T for d in S):
                        continue                       # not a MINIMAL subset
                    for combo in itertools.product(*[sorted(rs[j], key=sorted)
                                                     for j in S]):
                        u = frozenset().union(*combo) if combo else frozenset()
                        if any((b, 't') in u and (b, 'f') in u for b, _ in u):
                            continue                   # infeasible rail pair
                        acc.add(u)
                        if len(acc) > CUBE_CAP:
                            raise SystemExit("cube explosion in completeness "
                                             "analysis (raise CUBE_CAP)")
            acc = minimalize(acc)
            if A.get(out) != acc:
                A[out] = acc; stable = False
        if stable:
            break

    def req(net):
        cs = get(net)
        if not cs:
            return None
        r = None
        for c in cs:
            names = {b for b, _ in c}
            r = names if r is None else (r & names)
        return r

    cov = set()
    for pn, i, b in outbits:
        rt = req(railname(pn, i, ports[pn], "L", target))
        rf = req(railname(pn, i, ports[pn], "H", target))
        if rt is None or rf is None:
            continue
        got = rt & rf
        cov |= got
        if detail is not None:
            detail["%s[%d]" % (pn, i)] = sorted("%s[%d]" % inbits[x] for x in got)
    return cov


# ------------------------------------------------------------------- emission
def railname(pn, i, p, r, target):
    w = len(p["bits"])
    if target == "verilog":
        return "%s_%s[%d]" % (pn, r, i) if w > 1 else "%s_%s" % (pn, r)
    return "%s_%s(%d)" % (pn, r, i) if w > 1 else "%s_%s" % (pn, r)


def emit_verilog(top, ports, mp, extra_out, bind):
    L = ["// GENERATED by nulex map_ncl_direct.py --target verilog -- do not edit.",
         "// DIRECT-THRESHOLD dual-rail QDI netlist (natural TH cells, not DIMS).",
         "// Rails: <port>_L = value-1 (t), <port>_H = value-0 (f); NULL=(0,0)."]
    for cell in sorted(set(c for c, _, _ in mp.cells)):
        n = TH_PORTS[cell]
        pins = ", ".join("input %s" % p for p in ["a", "b", "c", "d"][:n])
        L.append("(* blackbox *) module %s(%s, output y); endmodule" % (cell, pins))
    pl = []
    for pn, p in ports.items():
        w = len(p["bits"]); d = "input" if p["direction"] == "input" else "output"
        rng = "" if w == 1 else "[%d:0] " % (w - 1)
        pl.append("%s %s%s_L" % (d, rng, pn)); pl.append("%s %s%s_H" % (d, rng, pn))
    for e in extra_out:
        pl.append("output %s" % e)
    L.append("module %s (%s);" % (top, ", ".join(pl)))
    for w in mp.wires:
        L.append("  wire %s;" % w)
    for i, (cell, ins, out) in enumerate(mp.cells):
        pn = ["a", "b", "c", "d"][:len(ins)]
        args = ", ".join(".%s(%s)" % (p, cv(s)) for p, s in zip(pn, ins))
        L.append("  %s u%d (%s, .y(%s));" % (cell, i, args, out))
    for lhs, rhs in mp.aliases:
        L.append("  assign %s = %s;" % (lhs, cv(rhs)))
    L.append("endmodule")
    return "\n".join(L) + "\n"


def cv(s):
    return {"0": "1'b0", "1": "1'b1"}.get(s, s)


def cvv(s):
    return {"0": "'0'", "1": "'1'"}.get(s, s)


def emit_vhdl(top, ports, mp, extra_out, bind):
    L = ["-- GENERATED by nulex map_ncl_direct.py --target vhdl -- do not edit.",
         "-- DIRECT-THRESHOLD dual-rail QDI netlist (th_cells.vhd instances).",
         "library IEEE; use IEEE.std_logic_1164.all;", "",
         "entity %s is" % top]
    pl = []
    for pn, p in ports.items():
        w = len(p["bits"]); d = "in" if p["direction"] == "input" else "out"
        ty = "std_logic" if w == 1 else "std_logic_vector(%d downto 0)" % (w - 1)
        pl.append("    %s_L : %s %s" % (pn, d, ty))
        pl.append("    %s_H : %s %s" % (pn, d, ty))
    for e in extra_out:
        pl.append("    %s : out std_logic" % e)
    L.append("  port (\n" + ";\n".join(pl) + "\n  );")
    L.append("end entity %s;" % top)
    L.append("architecture th_direct of %s is" % top)
    for i in range(0, len(mp.wires), 12):
        L.append("  signal " + ", ".join(mp.wires[i:i + 12]) + " : std_logic;")
    L.append("begin")
    for i, (cell, ins, out) in enumerate(mp.cells):
        pn = ["a", "b", "c", "d"][:len(ins)]
        args = ", ".join("%s => %s" % (p, cvv(s)) for p, s in zip(pn, ins))
        L.append("  u%d: entity work.%s(%s) port map (%s, y => %s);"
                 % (i, cell, bind, args, out))
    for lhs, rhs in mp.aliases:
        L.append("  %s <= %s;" % (lhs, cvv(rhs)))
    L.append("end architecture th_direct;")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
