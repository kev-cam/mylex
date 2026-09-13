#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L5 probe 3: a real critical path, judged by Xyce over the corners.
OpenROAD's timer names the ALU's worst path (`sta_worst.rpt`: a 30-stage
carry chain, 7 ns); a segment of it -- by default the six stages from
`_3674_` to `_3686_`, o311ai/a311oi pairs whose rising outputs are the slow
arcs -- is cut out of the routed layout with its wiring, its fan-out cells
and its row neighbours, extracted, and simulated: the layout's transistors
and the nets' distributed RC, the side inputs of every cell held at the
levels that make the path transparent (from the Liberty functions), the
segment delay from the first stage's input to the last stage's output at
tt / ss / ff.  Then a greedy search over fingers on the segment's cells,
each state re-extracted and simulated, cost = worst-corner delay +
0.5 dE/E, under the topology and delta-DRC guards.

    python3 probes/layopt/l5_xyce_critical.py [--name alu] [--from _3674_ --to _3686_] [--no-search] [--corners tt,ss,ff]
"""
import copy
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import drc as rules, extract, gds as gdsmod, lefdef, moves, optimize, rc, spice, tech   # noqa: E402

T = tech.SKY130
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
LEFS = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
GDS = os.path.join(ORFS, "sky130_fd_sc_hd.gds")
LIB = os.path.join(ORFS, "sky130_fd_sc_hd__tt_025C_1v80.lib")
NAME = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "alu"
FLOW = os.path.expanduser("~/src/%s-flow/hints" % NAME)
SCR = sys.argv[sys.argv.index("--scratch") + 1] if "--scratch" in sys.argv else os.environ.get("LAYOPT_SCRATCH", "/tmp")
CORN = (sys.argv[sys.argv.index("--corners") + 1] if "--corners" in sys.argv else "tt,ss,ff").split(",")
FROM = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else "_3674_"
TO = sys.argv[sys.argv.index("--to") + 1] if "--to" in sys.argv else "_3686_"
EVID = os.path.join(HERE, "evidence")
WIN_UM = 6.0


def sta_path(path):
    """[(inst, macro, in_pin, out_pin, delay_ns, in_edge, out_edge)] of the first path in an OpenSTA report."""
    stages, cur = [], None
    for ln in open(path):
        m = re.match(r"\s*(?:\d+\s+)?(?:[\d.]+\s+)?([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\^v])\s+(\S+)/(\S+)\s+\(sky130_fd_sc_hd__(\S+)\)", ln)
        if not m:
            if ln.startswith("Startpoint") and stages:
                break
            continue
        delay, edge, inst, pin, macro = float(m.group(2)), m.group(4), m.group(5), m.group(6), m.group(7)
        if cur is None or cur[0] != inst:
            cur = [inst, macro, pin, None, 0.0, edge, None]; stages.append(cur)
        else:
            cur[3] = pin; cur[4] = delay; cur[6] = edge
    return [tuple(s) for s in stages if s[3] is not None]


def liberty_functions(macros):
    txt = open(LIB).read()
    out = {}
    for m in macros:
        i = txt.find('cell ("sky130_fd_sc_hd__%s")' % m)
        if i < 0:
            continue
        j = txt.find("function", i)
        out[m] = re.search(r'function\s*:\s*"([^"]*)"', txt[j:j + 400]).group(1)
    return out


def sensitise(func, path_pin, pins):
    """levels for the other input pins so the output follows path_pin."""
    expr = func.replace("!", " not ").replace("&", " and ").replace("|", " or ").replace("^", " != ")
    side = [p for p in pins if p != path_pin]
    for bits in range(1 << len(side)):
        env = {p: bool((bits >> k) & 1) for k, p in enumerate(side)}
        env[path_pin] = False; y0 = bool(eval(expr, {}, env))
        env[path_pin] = True; y1 = bool(eval(expr, {}, env))
        if y0 != y1:
            return {p: env[p] for p in side}
    return {p: True for p in side}


def def_statements(text, section):
    """the '- ... ;' statements of a DEF section, as strings"""
    out, cur, inside = [], [], False
    for ln in text.split("\n"):
        st = ln.strip()
        if st.startswith(section + " "):
            inside = True; continue
        if inside and st.startswith("END " + section):
            break
        if not inside:
            continue
        if st.startswith("- ") and cur:
            out.append("\n".join(cur)); cur = []
        cur.append(ln)
        if st.endswith(";"):
            out.append("\n".join(cur)); cur = []
    return out


def reduced_def(text, keep_insts, keep_nets, out_path):
    head = text[:text.index("COMPONENTS ")]
    comps = [s for s in def_statements(text, "COMPONENTS") if re.match(r"\s*-\s+(\S+)", s).group(1) in keep_insts]
    snets = def_statements(text, "SPECIALNETS")
    nets = [s for s in def_statements(text, "NETS") if re.match(r"\s*-\s+(\S+)", s).group(1) in keep_nets]
    body = "COMPONENTS %d ;\n%s\nEND COMPONENTS\nSPECIALNETS %d ;\n%s\nEND SPECIALNETS\nNETS %d ;\n%s\nEND NETS\nEND DESIGN\n" % (
        len(comps), "\n".join(comps), len(snets), "\n".join(snets), len(nets), "\n".join(nets))
    open(out_path, "w").write(head + body)


def pin_shape(ex, lef, comp, pin, scale):
    m = lef.macros[comp.macro]
    lname, (a, b, c, d) = m.pins[pin].ports[0]
    ref, off = lefdef.place_transform(lef, comp.macro, comp.orient, int(round(comp.x * scale)), int(round(comp.y * scale)))
    r = gdsmod._xrect((int(round(a * 1000)), int(round(b * 1000)), int(round(c * 1000)), int(round(d * 1000))), ref, off)
    tl = {"li1": "li", "met1": "met1", "met2": "met2"}.get(lname, lname)
    return rc.shape_at(ex, tl, (r[0] + r[2]) / 2000.0, (r[1] + r[3]) / 2000.0)


def main():
    t0 = time.time()
    stages = sta_path(os.path.join(FLOW, "sta_worst.rpt"))
    names = [s[0] for s in stages]
    seg = stages[names.index(FROM):names.index(TO) + 1]
    print("== 1. OpenROAD's worst path: %d stages, %.2f ns; the segment %s..%s: %s (%.2f ns by the timer)" % (
        len(stages), sum(s[4] for s in stages), FROM, TO, " -> ".join("%s(%s)" % (s[0], s[1]) for s in seg), sum(s[4] for s in seg)))
    lef = lefdef.Lef()
    for f in LEFS:
        lefdef.read_lef(f, lef)
    base_def = os.path.join(FLOW, "%s_base.def" % NAME)
    d = lefdef.read_def(base_def); text = open(base_def).read()
    comps = {c.inst: c for c in d.components}
    scale = 1000.0 / d.dbu_per_um
    pin2net = {}
    for net in d.nets:
        for inst, pin in net.pins:
            pin2net[(inst, pin)] = net
    seg_insts = [s[0] for s in seg]
    seg_nets = [pin2net[(s[0], s[3])] for s in seg[:-1]] + [pin2net[(seg[0][0], seg[0][2])]]
    side = {inst for net in seg_nets for inst, _ in net.pins if inst in comps and inst not in seg_insts}
    keep = set(seg_insts) | side
    boxes = {}
    for c in d.components:
        m = lef.macros.get(c.macro)
        if m:
            boxes[c.inst] = (c.x, c.y, c.x + int(round(m.size[0] * d.dbu_per_um)), c.y + int(round(m.size[1] * d.dbu_per_um)))
    win = int(WIN_UM * d.dbu_per_um)
    for i in list(keep):
        if i not in boxes:
            continue
        x0, y0, x1, y1 = boxes[i]
        for j, (a, b, c2, e) in boxes.items():
            if b == y0 and a < x1 + win and c2 > x0 - win:
                keep.add(j)
    red = os.path.join(SCR, "l5c_%s_%s_%s.def" % (NAME, FROM.strip("_"), TO.strip("_")))
    reduced_def(text, keep, {n.name for n in seg_nets}, red)
    fl = lefdef.def2flat(red, LEFS, "", T, gds_lib=GDS)
    ex = extract.extract(fl, T)
    print("   reduced layout: %d cells (%d on the path, %d fan-out, the rest row neighbours), %d nets kept, %d rects, %d devices (%.0fs)" % (
        len(keep), len(seg_insts), len(side), len(seg_nets), len(fl.rects), len(ex.devices), time.time() - t0))
    funcs = liberty_functions({s[1] for s in seg})
    in_pins = {m: sorted(p for p, pin in lef.macros["sky130_fd_sc_hd__" + m].pins.items() if pin.use == "SIGNAL" and getattr(pin, "direction", "INPUT").startswith("INPUT")) for m in funcs}
    models = {c: spice.Models(T, c, scratch=os.path.join(SCR, "xyce_models")) for c in CORN}

    def simulate(ex_, tag):
        """{corner: {edge: (segment delay ps, energy fJ)}}"""
        s_in = pin_shape(ex_, lef, comps[seg[0][0]], seg[0][2], scale)
        s_out = pin_shape(ex_, lef, comps[seg[-1][0]], seg[-1][3], scale)
        tie = {}
        for inst, macro, ipin, opin, _, _, _ in seg:
            for p, lvl in sensitise(funcs[macro], ipin, in_pins[macro]).items():
                sid = pin_shape(ex_, lef, comps[inst], p, scale)
                if sid is not None:
                    tie[ex_.net_of_shape[sid]] = "vdd" if lvl else "vss"
        inv = sum(1 for s in seg if s[5] != s[6])          # inverting stages: the output edge for a given input edge
        out = {}
        for cname in CORN:
            corner = spice.Corner.named(cname); out[cname] = {}
            for edge in ("rise", "fall"):
                dk = spice.Deck(ex_, set(seg_insts), models[cname], corner)
                dk.tie_level.update(tie)
                dk.stimulus(s_in, edge=edge, slew_ps=80, period_ns=6.0)
                oedge = edge if inv % 2 == 0 else ("fall" if edge == "rise" else "rise")
                dk.measure("d_seg", (s_in, 0.5, edge), (s_out, 0.5, oedge))
                dk.measure_slew("tr_out", s_out, oedge)
                res = dk.run(os.path.join(SCR, "l5c_%s_%s_%s.cir" % (tag, edge, cname)), t_end_ns=9.0)
                if not res["_ok"] or res.get("d_seg") is None:
                    raise RuntimeError("Xyce failed (%s %s %s): %s" % (tag, edge, cname, res["_log"][-300:]))
                out[cname][edge] = (res["d_seg"] * 1e12, res.get("energy_fJ", 0.0), (res.get("tr_out") or 0) * 1e12)
        return out

    def worst(sim):
        w = max(v[0] for c in sim.values() for v in c.values())
        e = sum(v[1] for c in sim.values() for v in c.values()) / sum(len(c) for c in sim.values())
        return w, e
    sim0 = simulate(ex, "base"); w0, e0 = worst(sim0)
    print("== 2. Xyce, the segment as laid out (input %s/%s -> output %s/%s), both input edges:" % (seg[0][0], seg[0][2], seg[-1][0], seg[-1][3]))
    for c in CORN:
        print("   %-3s rise-in %7.1f ps (out slew %5.1f)  fall-in %7.1f ps (out slew %5.1f)  energy %.1f fJ" % (c, sim0[c]["rise"][0], sim0[c]["rise"][2], sim0[c]["fall"][0], sim0[c]["fall"][2], (sim0[c]["rise"][1] + sim0[c]["fall"][1]) / 2))
    print("   worst-corner segment delay %.1f ps (timer, tt: %.0f ps)" % (w0, 1000 * sum(s[4] for s in seg)))
    if "--no-search" in sys.argv:
        return
    sig = ex.signature(); base_keys = {rules.key(v) for v in rules.check(fl, ex)}
    prov = {inst: next(r.prov for r in fl.rects if "/%s/" % inst in r.prov) for inst in seg_insts}

    def fingers(inst, kind):
        def apply(f_, e_, n):
            t = []
            for _ in range(n - 1):
                e_ = extract.extract(f_, T)
                devs = [x for x in e_.devices if x.prov == prov[inst] and x.kind == kind]
                dev = max(devs, key=lambda x: max(e_.shapes[g].rect[2] for g in x.gate_ids))
                t += moves.add_finger(f_, e_, dev, side="high")
            return t
        return apply
    def vt(inst):
        """every PMOS of the stage to standard Vt (a series stack's gates go together)"""
        def apply(f_, e_, n):
            if n == 0:
                return []
            t = []
            for _ in range(8):
                e_ = extract.extract(f_, T)
                left = [x for x in e_.devices if x.prov == prov[inst] and x.kind == "p" and T.flavour_of_model(x.model) != "std"]
                if not left:
                    break
                t += moves.set_vt(f_, e_, left[0], "std")
            return t
        return apply
    variables = []
    for inst, macro, *_ in seg:
        for kind in ("p", "n"):
            variables.append(optimize.IntVariable("%s_%s" % (inst.strip("_"), kind), 1, 2, 1, fingers(inst, kind)))
        variables.append(optimize.IntVariable("%s_vt" % inst.strip("_"), 0, 1, 0, vt(inst)))
    counter = [0]
    def cost(f_, e_, x):
        counter[0] += 1
        sim = simulate(e_, "s%d" % counter[0]); w, e = worst(sim)
        return w / w0 + 0.5 * (e - e0) / e0, {"worst_ps": round(w, 1), "E_fJ": round(e, 1), "tt_rise": round(sim["tt"]["rise"][0], 1) if "tt" in sim else None}
    prob = optimize.DiscreteProblem(fl, T, variables, cost)
    if "--state" in sys.argv:
        # evaluate one given state (a dict of variable -> value) instead of searching
        import ast as _ast
        st = _ast.literal_eval(sys.argv[sys.argv.index("--state") + 1])
        x = [st.get(v.name, v.x0) for v in variables]
        best = prob.evaluate(x, keep=True)
        print("== 3. the given state, simulated at the corners")
    else:
        print("== 3. greedy search: a second finger on the P or N side of each stage, or its PMOS at standard Vt; every state simulated at the corners; cost = worst-corner delay + 0.5 dE/E")
        best = optimize.greedy_search(prob, verbose=True)
    sim1 = simulate(best.ex, "best"); w1, e1 = worst(sim1)
    print("== 4. result: %s" % {v.name: x for v, x in zip(variables, best.x) if x != v.x0})
    for c in CORN:
        print("   %-3s rise-in %7.1f ps (out slew %5.1f)  fall-in %7.1f ps (out slew %5.1f)  energy %.1f fJ" % (c, sim1[c]["rise"][0], sim1[c]["rise"][2], sim1[c]["fall"][0], sim1[c]["fall"][2], (sim1[c]["rise"][1] + sim1[c]["fall"][1]) / 2))
    print("   worst-corner segment delay %.1f -> %.1f ps (%.0f%%); energy %.1f -> %.1f fJ (%+.0f%%); legal=%s topology_ok=%s violations=%d; %d states, %d decks" % (
        w0, w1, 100 * (w1 - w0) / w0, e0, e1, 100 * (e1 - e0) / e0, best.legal, best.signature_ok, best.violations, len(prob.cache), counter[0] * 2 * len(CORN)))
    gdsmod.write_flat(best.fl, os.path.join(EVID, "l5_%s_critical_%s_%s.gds" % (NAME, FROM.strip("_"), TO.strip("_"))))


if __name__ == "__main__":
    main()
