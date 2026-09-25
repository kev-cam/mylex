#!/usr/bin/env python3
"""nulex map_ncl_direct_gl -- DIRECT-THRESHOLD mapper for GATE-LEVEL netlists.

map_ncl_direct.py maps a WORD-level yosys netlist one output cone at a time and
gives up when a cone's support exceeds 4 (MAXSUP).  That is fine for sha_slice
(8 bit, 3 outputs) but useless on a real block: alu_top's rs_data[0] cone reaches
most of the 278 primary inputs.  This module keeps map_ncl_direct's CONE MAPPER
(natural threshold -> minimum prime-implicant cover with don't-care presence)
and replaces the front end:

  * GATE-LEVEL primitives  $_AND_ $_OR_ $_XOR_ $_XNOR_ $_NAND_ $_NOR_ $_NOT_
    $_MUX_ $_DFF_P_.
  * NOT ELIMINATION BY POLARITY.  A dual-rail inverter is a rail swap, so every
    net reference is carried as (base_net, inv); $_NOT_ costs zero cells and can
    never appear inside a cone.
  * CONE TILING.  Cut points = primary inputs, register Q nets, constants and
    every net with fan-out > 1.  Cones are therefore single-fan-out TREES, so a
    cone absorbs a fan-in gate with NO logic duplication.  Each cone grows
    greedily from its root while its support stays <= --maxsup; a fan-in that
    would push it over becomes a new cut point and a new cone root.  The cones
    exactly TILE the netlist, which is what makes per-cone exhaustive checking a
    complete equivalence proof for the block.
  * GLOBAL PRESENCE CACHE.  presence(x) = TH12(x.t, x.f) is a property of the
    NET, not of the cone that needs it, so it is emitted once and shared.
  * LOCAL INPUT-COMPLETENESS, exact and cheap.  map_ncl_direct.check_completeness
    enumerates cubes over PRIMARY-INPUT rails; with 278 inputs and ~20k cells it
    never terminates.  Here completeness is enforced and checked PER CONE over
    that cone's own support rails, which is sound by the standard NCL
    composition argument (a network of input-complete function blocks with
    completion detection at the boundary is input-complete).
      --complete cone (default) : every cone is input-complete.  A natural
        threshold form is used only when BOTH rails pass the exact local check
        (enumerate feasible minimal asserting rail subsets, require every one to
        touch every support input); otherwise the cover form is used, which is
        input-complete by construction.
      --complete none : cheapest form always.  NOT QDI -- the bundled-data /
        external-completion control netlist.

  REGISTERS.  The emitted netlist is the COMBINATIONAL CLOUD only: every
  $_DFF_P_ Q net becomes an extra input rail pair (port qreg) and every D net an
  extra output rail pair (port dreg).  That makes the whole block a single
  acyclic dual-rail function that can be checked exhaustively per cone, and it
  keeps the register BINDING (sync-emulation / QDI ring / desync) an explicit,
  separately costed decision rather than something buried in a netlist.
  map_ncl_struct.py's QDI 4-phase pipeline binding REFUSES this design outright
  (map_ncl_struct.py:338-343, register feedback loop).

Usage:
  map_ncl_direct_gl.py <netlist.json> <top> <out.v>
      [--cells spice|full] [--maxsup 4] [--complete cone|none]
      [--cd none|tree] [--census out.json]
"""
import collections
import itertools
import json
import sys

sys.path.insert(0, "/usr/local/src/mylex/nulex")
import map_ncl_direct as MD

PINS = ["a", "b", "c", "d"]
_THRESH, _COVER = {}, {}


def find_threshold(tt, n):
    key = (n, tuple(sorted(tt.items())))
    if key not in _THRESH:
        _THRESH[key] = MD.find_threshold(tt, n)
    return _THRESH[key]


def min_cover(onset, n):
    key = (n, tuple(sorted(onset)))
    if key not in _COVER:
        _COVER[key] = MD.min_cover(onset, n)
    return _COVER[key]


# ------------------------------------------------- exact local completeness
def cell_complete(weights, thr, tags, nsup):
    """One threshold cell.  tags[i] = (support index, rail) of input i, or None
    for a constant rail (always DATA, never blocks).  True iff every FEASIBLE
    MINIMAL asserting subset of the inputs touches every one of the nsup support
    inputs -- i.e. the cell cannot assert before all of them are DATA."""
    n = len(weights)
    for k in range(1, n + 1):
        for S in itertools.combinations(range(n), k):
            if sum(weights[j] for j in S) < thr:
                continue
            if any(sum(weights[j] for j in S if j != dd) >= thr for dd in S):
                continue                                  # not minimal
            seen, bad = {}, False
            for j in S:
                if tags[j] is None:
                    continue
                s, r = tags[j]
                if seen.get(s, r) != r:
                    bad = True                            # both rails: infeasible
                    break
                seen[s] = r
            if bad:
                continue
            if len(seen) != nsup:
                return False
    return True


# ==================================================================== mapper
class GLMapper(MD.Mapper):
    def __init__(self, allowed, complete="cone"):
        MD.Mapper.__init__(self, allowed)
        self.complete = complete
        self.pres = {}
        self.style = collections.Counter()
        self.cells_by_style = collections.Counter()
        self.pres_cells = 0

    def presence(self, rt, rf):
        if rt in ("0", "1") or rf in ("0", "1"):
            return "1"                       # a constant rail pair is always DATA
        key = (rt, rf)
        if key not in self.pres:
            self.pres[key] = self.emit([1, 1], 1, [rt, rf])
            self.pres_cells += 1
        return self.pres[key]

    def map_cone(self, tt_fn, sup, rails, out_t, out_f):
        n = len(sup)
        tt = {}
        for x in itertools.product((0, 1), repeat=n):
            tt[x] = tt_fn(x)
        idx_on = {sum(xi << j for j, xi in enumerate(x)) for x, v in tt.items() if v}
        if not idx_on:
            self.aliases.append((out_t, "0")); self.aliases.append((out_f, "1"))
            self.style["const0"] += 1
            return "const0"
        if len(idx_on) == 1 << n:
            self.aliases.append((out_t, "1")); self.aliases.append((out_f, "0"))
            self.style["const1"] += 1
            return "const1"
        n0 = len(self.cells)

        th = find_threshold(tt, n)
        if th:
            w, T = th
            W = sum(w)
            okt = cell_complete(list(w), T, [(j, 't') for j in range(n)], n)
            okf = cell_complete(list(w), W - T + 1, [(j, 'f') for j in range(n)], n)
            if self.complete == "none" or (okt and okf):
                self.emit(list(w), T, [rails[s][0] for s in sup], out_t)
                self.emit(list(w), W - T + 1, [rails[s][1] for s in sup], out_f)
                st = "threshold" if (okt and okf) else "threshold_INCOMPLETE"
                self.style[st] += 1
                self.cells_by_style[st] += len(self.cells) - n0
                return st

        for rail, on in (("t", idx_on), ("f", set(range(1 << n)) - idx_on)):
            cov = min_cover(on, n)
            terms = []
            for mask, val in cov:
                lit, dc = [], []
                for j, s in enumerate(sup):
                    if mask >> j & 1:
                        lit.append(rails[s][0] if (val >> j & 1) else rails[s][1])
                    else:
                        dc.append(s)
                k, mdc = len(lit), len(dc)
                cand = None
                if k + 2 * mdc <= 4:
                    cand = MD.cell_for([1] * (k + 2 * mdc), k + mdc, self.allowed)
                if cand:
                    ins = lit + [r for s in dc for r in rails[s]]
                    terms.append(self.emit([1] * len(ins), k + mdc, ins))
                else:
                    ins = lit + [self.presence(*rails[s]) for s in dc]
                    ins = [x for x in ins if x != "1"]
                    if not ins:
                        terms.append("1")
                    else:
                        terms.append(self.emit([1] * len(ins), len(ins), ins))
            self.collect(terms, out_t if rail == "t" else out_f)
        self.style["cover"] += 1
        self.cells_by_style["cover"] += len(self.cells) - n0
        return "cover"


# ==================================================================== front end
GATE2 = {"$_AND_": "and", "$_OR_": "or", "$_XOR_": "xor", "$_XNOR_": "xnor",
         "$_NAND_": "nand", "$_NOR_": "nor"}
EVAL2 = {"and": lambda a, b: a & b, "or": lambda a, b: a | b,
         "xor": lambda a, b: a ^ b, "xnor": lambda a, b: 1 - (a ^ b),
         "nand": lambda a, b: 1 - (a & b), "nor": lambda a, b: 1 - (a | b)}


def bk(b):
    return b if isinstance(b, int) else str(b)


class Design(object):
    def __init__(self, mod):
        self.ports = mod["ports"]
        cells = mod["cells"]
        self.node, self.notsrc, self.regs = {}, {}, []
        self.clk = None
        for cn, c in cells.items():
            t = c["type"]
            if t == "$scopeinfo":
                continue
            cc = c["connections"]
            if t == "$_NOT_":
                self.notsrc[bk(cc["Y"][0])] = (bk(cc["A"][0]), 1)
            elif t in GATE2:
                self.node[bk(cc["Y"][0])] = (GATE2[t], [(bk(cc["A"][0]), 0),
                                                        (bk(cc["B"][0]), 0)])
            elif t == "$_MUX_":
                self.node[bk(cc["Y"][0])] = ("mux", [(bk(cc["S"][0]), 0),
                                                     (bk(cc["A"][0]), 0),
                                                     (bk(cc["B"][0]), 0)])
            elif t == "$_DFF_P_":
                self.regs.append([cn, (bk(cc["D"][0]), 0), bk(cc["Q"][0])])
                self.clk = bk(cc["C"][0])
            else:
                sys.exit("unhandled cell type %s (%s)" % (t, cn))
        for net in list(self.node):
            op, ins = self.node[net]
            self.node[net] = (op, [self.res(r) for r in ins])
        self.regs = [(n, self.res(d), q) for n, d, q in self.regs]
        self.inbits, self.outbits = collections.OrderedDict(), []
        for pn, p in self.ports.items():
            for i, b in enumerate(p["bits"]):
                if p["direction"] == "input":
                    self.inbits[bk(b)] = (pn, i)
                else:
                    self.outbits.append((pn, i, self.res((bk(b), 0))))

    def res(self, ref):
        net, inv = ref
        seen = set()
        while net in self.notsrc and net not in seen:
            seen.add(net)
            net, j = self.notsrc[net]
            inv ^= j
        return (net, inv)


def cone_support(des, gates):
    s = []
    for g in gates:
        for nn, _ in des.node[g][1]:
            if nn not in gates and nn not in ("0", "1") and nn not in s:
                s.append(nn)
    return s


def build(des, maxsup, maxgates=99):
    """Tile the design into single-fan-out cones of support <= maxsup and at most
    maxgates absorbed primitives (maxgates=1 -> one cone per primitive)."""
    qnets = {q for _, _, q in des.regs}
    fo = collections.Counter()
    for net, (op, ins) in des.node.items():
        for r, _ in ins:
            fo[r] += 1
    for _, (dnet, _), _ in des.regs:
        fo[dnet] += 1
    for pn, i, (b, inv) in des.outbits:
        fo[b] += 1
    cut = set(des.inbits) | qnets | {"0", "1", "x"} | {n for n in des.node if fo[n] > 1}
    roots, seen = collections.deque(), set()

    def addroot(n):
        if n in des.node and n not in seen:
            roots.append(n); seen.add(n)
    for _, (dnet, _), _ in des.regs:
        addroot(dnet)
    for pn, i, (b, inv) in des.outbits:
        addroot(b)
    for n in des.node:
        if n in cut:
            addroot(n)
    cones = []
    while roots:
        r = roots.popleft()
        gates = {r}
        sup = cone_support(des, gates)
        while len(gates) < maxgates:
            cands = [x for x in sup if x in des.node and x not in cut]
            best, bestsz = None, None
            for x in cands:
                g2 = gates | {x}
                sz = len(cone_support(des, g2))
                if sz <= maxsup and (bestsz is None or sz < bestsz):
                    best, bestsz = x, sz
            if best is None:
                break
            gates.add(best)
            sup = cone_support(des, gates)
        if len(sup) > maxsup:
            sys.exit("cone %s root support %d > maxsup %d" % (r, len(sup), maxsup))
        for x in sup:
            if x in des.node and x not in cut:
                cut.add(x); addroot(x)
        cones.append((r, sup, gates))
    return cut, cones


def ev(des, net, inv, env, gates):
    if net in gates:
        op, ins = des.node[net]
        vs = [ev(des, n, i, env, gates) for n, i in ins]
        v = (vs[2] if vs[0] else vs[1]) if op == "mux" else EVAL2[op](vs[0], vs[1])
    elif net == "0":
        v = 0
    elif net == "1":
        v = 1
    else:
        v = env[net]
    return v ^ inv


def rname(pn, p, i, r):
    return "%s_%s[%d]" % (pn, r, i) if len(p["bits"]) > 1 else "%s_%s" % (pn, r)


def main():
    argv = sys.argv[1:]

    def opt(n, dflt):
        return argv[argv.index(n) + 1] if n in argv else dflt
    cellset = opt("--cells", "spice")
    maxsup = int(opt("--maxsup", "4"))
    maxgates = int(opt("--maxgates", "99"))
    complete = opt("--complete", "cone")
    cd = opt("--cd", "none")
    cdscope = opt("--cd-scope", "all")
    census_out = opt("--census", None)
    flags = ("--cells", "--maxsup", "--maxgates", "--complete", "--cd", "--cd-scope", "--census")
    pos = [a for i, a in enumerate(argv)
           if a not in flags and (i == 0 or argv[i - 1] not in flags)]
    if len(pos) != 3:
        sys.exit(__doc__)
    jpath, top, out = pos
    if cellset == "spice":
        allowed = MD.SPICE_CELLS
    elif cellset == "full":
        allowed = MD.ALL_CELLS
    else:                       # e.g. "spice+th34": the characterized set plus
        allowed = MD.SPICE_CELLS | set(cellset.split("+")[1:])

    d = json.load(open(jpath))
    des = Design(d["modules"][top])
    cut, cones = build(des, maxsup, maxgates)
    mp = GLMapper(allowed, complete)

    rails = {"0": ("0", "1"), "1": ("1", "0")}
    skip = {des.clk}
    for b, (pn, i) in des.inbits.items():
        rails[b] = (rname(pn, des.ports[pn], i, "L"), rname(pn, des.ports[pn], i, "H"))
    for j, (_, _, q) in enumerate(des.regs):
        rails[q] = ("qreg_L[%d]" % j, "qreg_H[%d]" % j)
    for r, sup, gates in cones:
        rails[r] = ("n%s_L" % r, "n%s_H" % r)
        mp.wires += [rails[r][0], rails[r][1]]

    conemap = []
    for r, sup, gates in topo_cones(des, cones):
        ot, of = rails[r]
        fn = (lambda x, r=r, sup=sup, gates=gates:
              ev(des, r, 0, dict(zip(sup, x)), gates))
        sty = mp.map_cone(fn, sup, rails, ot, of)
        if sty in ("const0", "const1"):
            # A cone that collapsed to a CONSTANT must be handed downstream as a
            # literal, not as its (constant-driven) wire pair.  Otherwise the
            # next cone's presence(x.t, x.f) becomes TH12(1'b0, 1'b1), a cell
            # pinned high that can never return to NULL -- the same trap
            # Mapper.emit() guards against for constant cell inputs.  Caught by
            # verify_alu_direct.py CHECK 5 (400/400 nets stuck high).
            rails[r] = ("0", "1") if sty == "const0" else ("1", "0")
        tt = [0] * (1 << len(sup))
        for x in itertools.product((0, 1), repeat=len(sup)):
            tt[sum(xi << j for j, xi in enumerate(x))] = fn(x)
        conemap.append({"root": str(r), "support_rails": [list(rails[s]) for s in sup],
                        "out_L": ot, "out_H": of, "tt": tt,
                        "gates": len(gates)})

    def rails_of(ref):
        b, inv = ref
        t, f = rails[b]
        return (f, t) if inv else (t, f)

    outrails = []
    for pn, i, ref in des.outbits:
        ot = rname(pn, des.ports[pn], i, "L")
        of = rname(pn, des.ports[pn], i, "H")
        t, f = rails_of(ref)
        mp.aliases.append((ot, t)); mp.aliases.append((of, f))
        outrails.append((ot, of))
    for j, (_, dref, _) in enumerate(des.regs):
        t, f = rails_of(dref)
        mp.aliases.append(("dreg_L[%d]" % j, t))
        mp.aliases.append(("dreg_H[%d]" % j, f))
        outrails.append(("dreg_L[%d]" % j, "dreg_H[%d]" % j))

    logic_cells = len(mp.cells)
    logic_census = collections.Counter(c for c, _, _ in mp.cells)

    cd_cells, cd_depth = 0, 0
    if cd != "none":
        base = len(mp.cells)
        # Resolve every output rail through the alias chain FIRST.  A rail that
        # is tied to a constant is always DATA, so it must be left OUT of the
        # completion tree: a constant-1 input pins a hysteretic TH cell and the
        # detector could then never return to NULL (this is the same trap
        # Mapper.emit() guards against for constant cell inputs).
        al = {}
        for lhs, rhs in mp.aliases:
            al[lhs] = rhs

        def deref(x):
            seen = set()
            while x in al and x not in seen:
                seen.add(x); x = al[x]
            return x
        if cdscope == "po":
            src = outrails[:len(des.outbits)]
        else:
            src = outrails
        per, nconst = [], 0
        for t, f in src:
            t2, f2 = deref(t), deref(f)
            if t2 in ("0", "1") or f2 in ("0", "1"):
                nconst += 1
                continue
            per.append(mp.emit([1, 1], 1, [t2, f2]))
        per = [p for p in per if p not in ("0", "1")]
        lvl, cd_depth = per, 1
        while len(lvl) > 1:
            nxt = []
            for j in range(0, len(lvl), 2):
                nxt.append(mp.emit([1, 1], 2, lvl[j:j + 2]) if len(lvl[j:j + 2]) == 2
                           else lvl[j])
            lvl = nxt; cd_depth += 1
        mp.aliases.append(("done", lvl[0]))
        cd_cells = len(mp.cells) - base

    census = collections.Counter(c for c, _, _ in mp.cells)
    info = {"top": top, "maxsup": maxsup, "maxgates": maxgates, "complete": complete, "cellset": cellset,
            "cd": cd, "n_cones": len(cones),
            "cone_styles": dict(mp.style), "cells_by_style": dict(mp.cells_by_style),
            "cone_support_hist": dict(collections.Counter(len(s) for _, s, _ in cones)),
            "gates_per_cone_hist": dict(collections.Counter(len(g) for _, _, g in cones)),
            "presence_cells": mp.pres_cells,
            "logic_cells": logic_cells, "logic_census": dict(logic_census),
            "cd_cells": cd_cells, "cd_levels": cd_depth, "cd_scope": cdscope,
            "cd_bits": len(per) if cd != "none" else 0,
            "cd_constant_bits_skipped": nconst if cd != "none" else 0,
            "n_regs": len(des.regs), "total": sum(census.values()),
            "census": dict(census)}
    open(out, "w").write(emit_v(top, des, mp, cd != "none", len(des.regs)))
    if census_out:
        json.dump(info, open(census_out, "w"), indent=1)
        json.dump({"top": top, "cones": conemap},
                  open(census_out.replace(".json", "_cones.json"), "w"))
    print(json.dumps(info, indent=1))


def topo_cones(des, cones):
    byroot = {r: (r, s, g) for r, s, g in cones}
    state, out = {}, []
    sys.setrecursionlimit(200000)

    def go(r):
        st = state.get(r)
        if st == 2:
            return
        if st == 1:
            sys.exit("combinational loop through net %s" % r)
        state[r] = 1
        for s in byroot[r][1]:
            if s in byroot:
                go(s)
        state[r] = 2
        out.append(byroot[r])
    for r, _, _ in cones:
        go(r)
    return out


def emit_v(top, des, mp, has_cd, nreg):
    L = ["// GENERATED by nulex map_ncl_direct_gl.py -- do not edit.",
         "// DIRECT-THRESHOLD dual-rail netlist, gate-level front end.",
         "// Rails: <port>_L = value-1 (t), <port>_H = value-0 (f); NULL=(0,0).",
         "// qreg_* = register Q rails (inputs), dreg_* = register D rails (outputs)."]
    for cell in sorted({c for c, _, _ in mp.cells}):
        pins = ", ".join("input %s" % p for p in PINS[:MD.TH_PORTS[cell]])
        L.append("(* blackbox *) module %s(%s, output y); endmodule" % (cell, pins))
    pl = []
    for pn, p in des.ports.items():
        w = len(p["bits"])
        dr = "input" if p["direction"] == "input" else "output"
        rng = "" if w == 1 else "[%d:0] " % (w - 1)
        pl.append("%s %s%s_L" % (dr, rng, pn)); pl.append("%s %s%s_H" % (dr, rng, pn))
    if nreg:
        pl.append("input [%d:0] qreg_L" % (nreg - 1))
        pl.append("input [%d:0] qreg_H" % (nreg - 1))
        pl.append("output [%d:0] dreg_L" % (nreg - 1))
        pl.append("output [%d:0] dreg_H" % (nreg - 1))
    if has_cd:
        pl.append("output done")
    L.append("module %s (%s);" % (top, ", ".join(pl)))
    dcl = sorted(set(mp.wires))
    for i in range(0, len(dcl), 16):
        L.append("  wire " + ", ".join(dcl[i:i + 16]) + ";")
    for i, (cell, ins, o) in enumerate(mp.cells):
        args = ", ".join(".%s(%s)" % (p, MD.cv(s)) for p, s in zip(PINS, ins))
        L.append("  %s u%d (%s, .y(%s));" % (cell, i, args, o))
    for lhs, rhs in mp.aliases:
        L.append("  assign %s = %s;" % (lhs, MD.cv(rhs)))
    L.append("endmodule")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
