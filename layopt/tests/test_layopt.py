# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Self-contained checks (no external files): a synthetic sky130 inverter is
written, read back, extracted, resized and rule-checked.  If the kestrel PLL
GDS + KLayout golden netlist are present, the isomorphism check runs too.

Run:  python3 -m layopt.tests.test_layopt
"""
import os
import sys
import tempfile

from .. import compare, drc, extract, gds, geom, moves, rc, tech

T = tech.SKY130
K = os.environ.get("KESTREL_DIR", "/usr/local/src/kestrel")


def _r(fl, layer, x0, y0, x1, y1, prov):
    moves.add_rect(fl, T.layers[layer], (x0, y0, x1, y1), prov)


def synthetic_inverter():
    """NFET W=1.0 L=0.15 at the bottom, PFET W=2.0 L=0.15 in an nwell 3 um
    higher; poly gate shared; drains strapped with li; sources contacted."""
    fl = gds.FlatLayout(dbu_um=0.001, top="inv")
    _r(fl, "diff", 0.0, 0.0, 1.15, 1.0, "inv/mn"); _r(fl, "nsdm", -0.1, -0.1, 1.25, 1.1, "inv/mn")
    _r(fl, "poly", 0.5, -0.13, 0.65, 1.13, "inv/mn")
    _r(fl, "nwell", -0.5, 3.5, 1.65, 6.2, "inv/mp"); _r(fl, "psdm", -0.1, 3.9, 1.25, 6.1, "inv/mp")
    _r(fl, "diff", 0.0, 4.0, 1.15, 6.0, "inv/mp")
    _r(fl, "poly", 0.5, 3.87, 0.65, 6.13, "inv/mp")
    _r(fl, "poly", 0.5, 1.13, 0.65, 3.87, "inv")                # gate connection, owned by the cell
    for y in (0.2, 0.55):
        _r(fl, "licon", 0.16, y, 0.33, y + 0.17, "inv/mn"); _r(fl, "licon", 0.82, y, 0.99, y + 0.17, "inv/mn")
    for y in (4.2, 4.6, 5.0, 5.4):
        _r(fl, "licon", 0.16, y, 0.33, y + 0.17, "inv/mp"); _r(fl, "licon", 0.82, y, 0.99, y + 0.17, "inv/mp")
    _r(fl, "li", 0.08, 0.1, 0.41, 0.9, "inv/mn"); _r(fl, "li", 0.08, 4.1, 0.41, 5.9, "inv/mp")
    _r(fl, "li", 0.74, 0.1, 1.07, 5.9, "inv")                    # drain strap n<->p, owned by the cell
    return fl


def test_geom():
    assert geom.subtract((0, 0, 10, 4), [(3, -1, 4, 5)]) == [(0, 0, 3, 4), (4, 0, 10, 4)]
    assert geom.union_area_perimeter([(0, 0, 2, 2), (1, 1, 3, 3)]) == (7, 12)
    assert geom.touches((0, 0, 1, 1), (1, 0, 2, 1)) and not geom.touches((0, 0, 1, 1), (1, 1, 2, 2))


def test_inverter_roundtrip_extract_resize():
    fl = synthetic_inverter()
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "inv.gds")
        gds.write_flat(fl, p)
        fl2 = gds.flatten(gds.read(p))
    assert sorted((r.layer, r.rect) for r in fl.rects) == sorted((r.layer, r.rect) for r in fl2.rects)
    ex = extract.extract(fl2, T)
    kinds = sorted((d.kind, round(d.w, 3), round(d.l, 3)) for d in ex.devices)
    assert kinds == [("n", 1.0, 0.15), ("p", 2.0, 0.15)], kinds
    mn, mp = sorted(ex.devices, key=lambda d: d.kind)
    assert mn.g == mp.g, "shared gate"
    assert len({mn.s, mn.d} & {mp.s, mp.d}) == 1, "one shared S/D net (out)"
    x = rc.net_rc(ex, mn.g)
    assert x.c_fF > 0
    # resize the NFET to W=1.5: topology preserved, W updated
    sig = ex.signature()
    touched = moves.resize_device_w(fl2, ex, mn, 1.5)
    ex2 = extract.extract(fl2, T)
    mn2 = [d for d in ex2.devices if d.kind == "n"][0]
    assert abs(mn2.w - 1.5) < 1e-6 and ex2.signature() == sig and touched
    # pushing into the PFET row must be caught
    fl3 = synthetic_inverter(); ex3 = extract.extract(fl3, T)
    base = {drc.key(v) for v in drc.check(fl3, ex3)}
    t3 = moves.resize_device_w(fl3, ex3, [d for d in ex3.devices if d.kind == "n"][0], 3.8)
    ex4 = extract.extract(fl3, T)
    assert drc.new_violations(fl3, ex4, t3, base), "expected a spacing violation"


def test_kestrel_golden():
    g = os.path.join(K, "layout", "kestrel_pll.gds")
    ref = os.path.join(K, "layout", "kestrel_pll_flat_extracted.cir")
    if not (os.path.exists(g) and os.path.exists(ref)):
        print("  (kestrel not found at %s, skipped)" % K); return
    ex = extract.extract(gds.flatten(gds.read(g)), T)
    r = compare.compare_to_reference(ex, ref)
    assert r["wl_match"] and r["isomorphic"] and r["degree_hist_match"] and r["area_perim_match"], r


def test_lefdef_inline():
    """LEF/DEF reader on inline text: tech layers/vias, a macro with pins, a DEF
    with two placed components (one flipped) and one routed net with vias."""
    from .. import lefdef
    tlef = """VERSION 5.7 ; UNITS DATABASE MICRONS 1000 ; END UNITS
PROPERTYDEFINITIONS LAYER LEF58_TYPE STRING ; END PROPERTYDEFINITIONS
SITE unit SYMMETRY Y ; CLASS CORE ; SIZE 0.46 BY 2.72 ; END unit
LAYER li1 TYPE ROUTING ; WIDTH 0.17 ; END li1
LAYER mcon TYPE CUT ; WIDTH 0.17 ; END mcon
LAYER met1 TYPE ROUTING ; WIDTH 0.14 ; END met1
VIA L1M1 DEFAULT LAYER mcon ; RECT -0.085 -0.085 0.085 0.085 ; LAYER li1 ; RECT -0.085 -0.085 0.085 0.085 ;
  LAYER met1 ; RECT -0.145 -0.115 0.145 0.115 ; END L1M1
LAYER via TYPE CUT ; WIDTH 0.15 ; END via
LAYER met2 TYPE ROUTING ; WIDTH 0.14 ; END met2
VIA M1M2 DEFAULT LAYER via ; RECT -0.075 -0.075 0.075 0.075 ; LAYER met1 ; RECT -0.16 -0.13 0.16 0.13 ;
  LAYER met2 ; RECT -0.13 -0.16 0.13 0.16 ; END M1M2
END LIBRARY"""
    lef = """MACRO inv CLASS CORE ; ORIGIN 0 0 ; SIZE 1.38 BY 2.72 ; SITE unit ;
PIN A DIRECTION INPUT ; USE SIGNAL ; PORT LAYER li1 ; RECT 0.32 1.075 0.65 1.315 ; END END A
PIN VPWR USE POWER ; PORT LAYER met1 ; RECT 0 2.48 1.38 2.96 ; END END VPWR
OBS END END inv END LIBRARY"""
    deftext = """VERSION 5.8 ; DESIGN t ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 2760 5440 ) ;
COMPONENTS 2 ; - u1 inv + PLACED ( 0 0 ) N ; - u2 inv + PLACED ( 0 2720 ) FS ; END COMPONENTS
SPECIALNETS 1 ; - VPWR ( u1 VPWR ) ( u2 VPWR ) + USE POWER ; END SPECIALNETS
NETS 1 ; - n ( u1 A ) ( u2 A ) + ROUTED met1 ( 485 1195 ) L1M1 NEW met1 ( 485 1195 ) M1M2 NEW met2 ( 485 1195 ) ( 485 4245 ) NEW met1 ( 485 4245 ) M1M2 NEW met1 ( 485 4245 ) L1M1 ; END NETS
END DESIGN"""
    with tempfile.TemporaryDirectory() as td:
        for name, txt in (("t.tlef", tlef), ("inv.lef", lef), ("t.def", deftext)):
            open(os.path.join(td, name), "w").write(txt)
        L = lefdef.read_lef(os.path.join(td, "t.tlef")); lefdef.read_lef(os.path.join(td, "inv.lef"), L)
        assert L.layers["met1"].width_um == 0.14 and len(L.vias["L1M1"].rects) == 3, L.vias["L1M1"]
        assert L.macros["inv"].size == (1.38, 2.72) and L.macros["inv"].pins["A"].ports[0][0] == "li1"
        d = lefdef.read_def(os.path.join(td, "t.def"))
        assert [(c.inst, c.x, c.y, c.orient) for c in d.components] == [("u1", 0, 0, "N"), ("u2", 0, 2720, "FS")]
        nets = {n.name: n for n in d.nets}
        assert nets["n"].wires[0].via == "L1M1" and any(w.layer == "met2" and w.points == [(485, 1195), (485, 4245)] for w in nets["n"].wires)
        assert nets["VPWR"].special and nets["VPWR"].pins == [("u1", "VPWR"), ("u2", "VPWR")]
        # a real cell placed twice, FS row on top: VPWR rails must abut into one net
        lib = os.path.expanduser("~/tools/sky130_fd_sc_hd")
        if os.path.exists(os.path.join(lib, "sky130_fd_sc_hd__inv_1.gds")):
            deftext2 = deftext.replace(" inv ", " sky130_fd_sc_hd__inv_1 ").replace("L1M1", "L1M1_PR").replace("M1M2", "M1M2_PR")
            open(os.path.join(td, "t2.def"), "w").write(deftext2)
            fl = lefdef.def2flat(os.path.join(td, "t2.def"), [os.path.join(lib, "sky130_fd_sc_hd.tlef"), os.path.join(lib, "sky130_fd_sc_hd__inv_1.lef")], lib, T)
            ex = extract.extract(fl, T)
            assert len(ex.devices) == 4 and {d.prov.split("/")[1] for d in ex.devices} == {"u1", "u2"}
            nn = [n for n in ex.nets.values() if n.name == "n"]
            assert len(nn) == 1 and sorted(t for _, t in nn[0].devices) == ["G", "G", "G", "G"], nn[0].devices if nn else None
            vp = [n for n in ex.nets.values() if n.name == "VPWR"]
            insts = {ex.shapes[s].prov.split("/")[1] for n in vp for s in n.shapes if ex.shapes[s].prov.count("/") >= 2}
            assert len(vp) == 1 and insts >= {"u1", "u2"} and len(vp[0].devices) == 2, \
                "VPWR rails of the N and FS rows should abut into one net (one PMOS source each)"
        else:
            print("  (sky130_fd_sc_hd cells not found, geometric part skipped)")


def test_elmore_single_wire():
    """Distributed-RC Elmore on one met2 wire: R_drv*C_total + R*C_wire/2 + R*C_in."""
    fl = gds.FlatLayout(dbu_um=0.001, top="w")
    L, w = 100.0, 0.14                                 # um
    _r(fl, "met2", 0.0, 0.0, L, w, "w/wire")
    _r(fl, "met2", -0.2, -0.03, 0.0, w + 0.03, "w/drv")   # driver pad touching the left end
    _r(fl, "met2", L, -0.03, L + 0.2, w + 0.03, "w/rcv")  # receiver pad touching the right end
    ex = extract.extract(fl, T)
    net = ex.net_of_shape[0]
    ids = {ex.shapes[s].prov: s for s in ex.nets[net].shapes}
    drv, rcv, wire = ids["w/drv"], ids["w/rcv"], ids["w/wire"]
    r_drv, c_in = 3000.0, 2.0
    got = rc.elmore_delays(ex, net, drv, [rcv], r_drv, {rcv: c_in})[rcv]
    R = T.rsh["met2"] * L / w
    cw = rc.shape_c_fF(ex, wire); c_tot = sum(rc.shape_c_fF(ex, s) for s in (drv, rcv, wire)) + c_in
    c_rcv = rc.shape_c_fF(ex, rcv) + c_in
    want = (r_drv * c_tot + R * cw / 2 + R * c_rcv) * 1e-3
    assert abs(got - want) / want < 0.02, (got, want, R)


def test_add_finger_inv1():
    """Dissolve move on a real cell: inv_1 next to a fill_4; adding a finger to
    each transistor doubles W, keeps the netlist, and is rule-clean."""
    from .. import lefdef, moves as mv, drc as rules
    lib = os.path.expanduser("~/tools/sky130_fd_sc_hd")
    if not os.path.exists(os.path.join(lib, "sky130_fd_sc_hd__fill_4.gds")):
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    deftext = """VERSION 5.8 ; DESIGN t ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 4600 2720 ) ;
COMPONENTS 3 ; - f1 sky130_fd_sc_hd__fill_4 + PLACED ( 0 0 ) N ; - u1 sky130_fd_sc_hd__inv_1 + PLACED ( 1840 0 ) N ;
- f2 sky130_fd_sc_hd__fill_4 + PLACED ( 3220 0 ) N ; END COMPONENTS
SPECIALNETS 2 ; - VPWR ( u1 VPWR ) + USE POWER ; - VGND ( u1 VGND ) + USE GROUND ; END SPECIALNETS
END DESIGN"""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "t.def"), "w").write(deftext)
        lefs = [os.path.join(lib, f) for f in ("sky130_fd_sc_hd.tlef", "sky130_fd_sc_hd__inv_1.lef", "sky130_fd_sc_hd__fill_4.lef")]
        fl = lefdef.def2flat(os.path.join(td, "t.def"), lefs, lib, T)
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    for kind, w0 in (("p", 1.0), ("n", 0.65)):
        ex = extract.extract(fl, T)
        dev = [d for d in ex.devices if d.kind == kind][0]
        assert abs(dev.w - w0) < 1e-6
        touched = mv.add_finger(fl, ex, dev, side="high")
        ex2 = extract.extract(fl, T)
        d2 = [d for d in ex2.devices if d.kind == kind][0]
        assert abs(d2.w - 2 * w0) < 1e-6 and d2.fingers == 2, (d2.w, d2.fingers)
        assert len(ex2.devices) == 2 and ex2.signature() == sig
        assert not rules.new_violations(fl, ex2, touched, base), rules.new_violations(fl, ex2, touched, base)
        base = {rules.key(v) for v in rules.check(fl, ex2)}
    # the cell's diffusion now crosses its LEF box (x = 1.84 + 1.38 = 3.22 um)
    assert max(r.x1 for r in fl.rects if r.layer == T.layers["diff"] and "u1" in r.prov) > 3220
    # a third PMOS finger: its outer S/D is the drain (signal net Y) -> needs the mcon/met1 jumper
    ex = extract.extract(fl, T)
    dev = [d for d in ex.devices if d.kind == "p"][0]
    touched = mv.add_finger(fl, ex, dev, side="high")
    ex3 = extract.extract(fl, T)
    d3 = [d for d in ex3.devices if d.kind == "p"][0]
    assert abs(d3.w - 3.0) < 1e-6 and d3.fingers == 3 and ex3.signature() == sig, (d3.w, d3.fingers)
    assert any(fl.rects[i].layer == T.layers["met1"] for i in touched), "jumper expected on met1"
    assert not rules.new_violations(fl, ex3, touched, base), rules.new_violations(fl, ex3, touched, base)


def test_def_vias():
    """DEF VIAS: a VIARULE-generated 1x2 via and an explicit RECT via."""
    from .. import lefdef
    txt = """VERSION 5.8 ; DESIGN v ; UNITS DISTANCE MICRONS 1000 ;
VIAS 2 ;
- via_gen + VIARULE M1M2_PR + CUTSIZE 150 150 + LAYERS met1 via met2 + CUTSPACING 170 170 + ENCLOSURE 85 165 55 85 + ROWCOL 1 2 ;
- via_rect + RECT met1 ( -100 -100 ) ( 100 100 ) + RECT via ( -75 -75 ) ( 75 75 ) + RECT met2 ( -100 -100 ) ( 100 100 ) ;
END VIAS
END DESIGN"""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "v.def"), "w").write(txt)
        d = lefdef.read_def(os.path.join(td, "v.def"))
    g = d.vias["via_gen"]
    cuts = [r for l, r in g.rects if l == "via"]
    assert len(cuts) == 2 and abs((cuts[1][0] - cuts[0][0]) - 0.32) < 1e-9, cuts          # pitch = 0.15 + 0.17
    m1 = [r for l, r in g.rects if l == "met1"][0]
    assert abs((m1[2] - m1[0]) - (0.47 + 2 * 0.085)) < 1e-9 and abs((m1[3] - m1[1]) - (0.15 + 2 * 0.165)) < 1e-9, m1
    assert len(d.vias["via_rect"].rects) == 3 and d.vias["via_rect"].rects[1][1] == (-0.075, -0.075, 0.075, 0.075)


def test_contact_and_column_bridge_inv1():
    """Forced contact mode on inv_1 beside a fill_4: the PMOS finger ties its gate
    through a poly tab + licon + li pad + met1 jumper to the A pin; the NMOS
    finger then joins the PMOS finger's poly with a column bridge.  Both legal."""
    from .. import lefdef, moves as mv, drc as rules
    lib = os.path.expanduser("~/tools/sky130_fd_sc_hd")
    if not os.path.exists(os.path.join(lib, "sky130_fd_sc_hd__fill_4.gds")):
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    deftext = """VERSION 5.8 ; DESIGN t ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 4600 2720 ) ;
COMPONENTS 3 ; - f1 sky130_fd_sc_hd__fill_4 + PLACED ( 0 0 ) N ; - u1 sky130_fd_sc_hd__inv_1 + PLACED ( 1840 0 ) N ;
- f2 sky130_fd_sc_hd__fill_4 + PLACED ( 3220 0 ) N ; END COMPONENTS
SPECIALNETS 2 ; - VPWR ( u1 VPWR ) + USE POWER ; - VGND ( u1 VGND ) + USE GROUND ; END SPECIALNETS
END DESIGN"""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "t.def"), "w").write(deftext)
        lefs = [os.path.join(lib, f) for f in ("sky130_fd_sc_hd.tlef", "sky130_fd_sc_hd__inv_1.lef", "sky130_fd_sc_hd__fill_4.lef")]
        fl = lefdef.def2flat(os.path.join(td, "t.def"), lefs, lib, T)
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    layers_added = {}
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        dev = [d for d in ex.devices if d.kind == kind][0]
        n0 = len(fl.rects)
        touched = mv.add_finger(fl, ex, dev, side="high", bridge="contact")
        ex2 = extract.extract(fl, T)
        d2 = [d for d in ex2.devices if d.kind == kind][0]
        assert d2.fingers == 2 and ex2.signature() == sig, (kind, d2.fingers)
        assert not rules.new_violations(fl, ex2, touched, base), rules.new_violations(fl, ex2, touched, base)
        layers_added[kind] = {fl.rects[i].layer for i in touched if i >= n0}
        base = {rules.key(v) for v in rules.check(fl, ex2)}
    inv = {v: k for k, v in T.layers.items()}
    assert {"met1", "mcon", "licon"} <= {inv[l] for l in layers_added["p"]}, "PMOS should use the contact bridge"
    assert "met1" not in {inv[l] for l in layers_added["n"]}, "NMOS should use the column bridge (poly only)"


def test_series_stack_nand2():
    """A nand2_1 beside a fill_8 with no routing in the way: the PMOS finger
    (parallel pair) and the NMOS finger (series stack: both gates and the
    uncontacted middle node mirrored, the far gate bridged by contact) are
    both legal and keep the netlist."""
    from .. import lefdef, moves as mv, drc as rules
    lib = os.path.expanduser("~/tools/sky130_fd_sc_hd")
    if not os.path.exists(os.path.join(lib, "sky130_fd_sc_hd__fill_8.gds")):
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    deftext = """VERSION 5.8 ; DESIGN t ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 6900 2720 ) ;
COMPONENTS 3 ; - f1 sky130_fd_sc_hd__fill_4 + PLACED ( 0 0 ) N ; - u1 sky130_fd_sc_hd__nand2_1 + PLACED ( 1840 0 ) N ;
- f2 sky130_fd_sc_hd__fill_8 + PLACED ( 3220 0 ) N ; END COMPONENTS
SPECIALNETS 2 ; - VPWR ( u1 VPWR ) + USE POWER ; - VGND ( u1 VGND ) + USE GROUND ; END SPECIALNETS
END DESIGN"""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "t.def"), "w").write(deftext)
        lefs = [os.path.join(lib, f) for f in ("sky130_fd_sc_hd.tlef", "sky130_fd_sc_hd__nand2_1.lef", "sky130_fd_sc_hd__fill_4.lef", "sky130_fd_sc_hd__fill_8.lef")]
        fl = lefdef.def2flat(os.path.join(td, "t.def"), lefs, lib, T)
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    # order matters in a 0.6 um field gap (the second finger's bridge has to
    # dodge the first's); the claim is that one order legalizes both
    import copy
    fl0 = fl
    best = None
    for order in (("p", "n"), ("n", "p")):
        fl = copy.deepcopy(fl0)
        base0 = set(base)
        done = []
        for kind in order:
            ex = extract.extract(fl, T)
            devs = [d for d in ex.devices if d.kind == kind]
            devs.sort(key=lambda x: -max(ex.shapes[g].rect[2] for g in x.gate_ids))
            try:
                touched = mv.add_finger(fl, ex, devs[0], side="high")
            except mv.MoveError as e:
                print("  (%s: %s finger refused after %s: %s)" % ("".join(order), kind, done, str(e)[:90])); continue
            ex2 = extract.extract(fl, T)
            assert ex2.signature() == sig, kind
            nv = rules.new_violations(fl, ex2, touched, base0)
            if nv:
                print("  (%s: %s finger illegal after %s: %s)" % ("".join(order), kind, done, nv[:2])); continue
            base0 = {rules.key(v) for v in rules.check(fl, ex2)}
            done.append(kind)
        print("  order %s: legal %s" % ("".join(order), done))
        if best is None or len(done) > len(best[1]):
            best = (fl, done)
        if len(done) == 2:
            break
    fl, done = best
    ex2 = extract.extract(fl, T)
    assert "n" in done, "the NMOS series stack must mirror legally on a bare row"
    assert "p" in done, "the PMOS finger must be legal alongside the mirrored stack in one order"
    # NMOS stack: the whole stack mirrored, i.e. two parallel A-B stacks with
    # their own uncontacted middle nodes (sky130's nand2_2 style); they extract
    # as four 0.65 devices and the stack-canonical signature folds them
    n = [x for x in ex2.devices if x.kind == "n"]
    assert len(n) == 4 and all(abs(x.w - 0.65) < 1e-6 for x in n), {(x.kind, round(x.w, 2)) for x in ex2.devices}
    assert sum(1 for x in ex2.devices if x.kind == "p" and abs(x.w - 2.0) < 1e-6) == 1
    from .. import compare
    devs, netmap = compare.reduce_stacks(ex2)
    assert len(netmap) == 1, netmap                       # one middle node identified with the other




def test_route_around_met1():
    """The bare nand2 row with a foreign met1 wire laid straight through the
    field gap where the far gate's contact bridge would put its bar: the
    bridge must route around it (li up, met1/met2 across, landing on the gate
    net's own li or met1) and the netlist must survive."""
    from .. import lefdef, moves as mv, drc as rules
    lib = os.path.expanduser("~/tools/sky130_fd_sc_hd")
    if not os.path.exists(os.path.join(lib, "sky130_fd_sc_hd__fill_8.gds")):
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    deftext = """VERSION 5.8 ; DESIGN t ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 6900 2720 ) ;
COMPONENTS 3 ; - f1 sky130_fd_sc_hd__fill_4 + PLACED ( 0 0 ) N ; - u1 sky130_fd_sc_hd__nand2_1 + PLACED ( 1840 0 ) N ;
- f2 sky130_fd_sc_hd__fill_8 + PLACED ( 3220 0 ) N ; END COMPONENTS
SPECIALNETS 2 ; - VPWR ( u1 VPWR ) + USE POWER ; - VGND ( u1 VGND ) + USE GROUND ; END SPECIALNETS
END DESIGN"""
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "t.def"), "w").write(deftext)
        lefs = [os.path.join(lib, f) for f in ("sky130_fd_sc_hd.tlef", "sky130_fd_sc_hd__nand2_1.lef", "sky130_fd_sc_hd__fill_4.lef", "sky130_fd_sc_hd__fill_8.lef")]
        fl = lefdef.def2flat(os.path.join(td, "t.def"), lefs, lib, T)
    # a P&R-style met1 wire of some other net across the whole gap (y 1.05..1.19 um)
    mv.add_rect_dbu(fl, T.layers["met1"], (1500, 1050, 5500, 1190), "t/net:blocker")
    ex = extract.extract(fl, T)
    sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        devs = [d for d in ex.devices if d.kind == kind]
        devs.sort(key=lambda x: -max(ex.shapes[g].rect[2] for g in x.gate_ids))
        touched = mv.add_finger(fl, ex, devs[0], side="high")
        ex2 = extract.extract(fl, T)
        assert ex2.signature() == sig, kind
        nv = rules.new_violations(fl, ex2, touched, base)
        assert not nv, (kind, nv[:3])
        base = {rules.key(v) for v in rules.check(fl, ex2)}
    stats = mv.LAST_PLAN_TALLY.get("maze route")
    assert stats and stats.get("path_cells"), mv.LAST_PLAN_TALLY
    print("  routed around the blocker: %d cells, cost %d" % (stats["path_cells"], stats["cost"]))


def test_same_net_notch():
    """Two parts of one net closer than spacing without touching are a notch;
    the same pair with the gap filled by a third rectangle is one polygon and
    legal; different-net spacing is unchanged."""
    from .. import drc as rules, gds as g
    fl = g.FlatLayout(dbu_um=0.001, top="t", rects=[])
    li = T.layers["li"]
    # a U of li: two arms 0.10 um apart on a base -- one net
    base = moves.add_rect_dbu(fl, li, (0, 0, 1000, 200), "t/u")
    arm_a = moves.add_rect_dbu(fl, li, (0, 200, 300, 1000), "t/u")
    arm_b = moves.add_rect_dbu(fl, li, (400, 200, 1000, 1000), "t/u")
    ex = extract.extract(fl, T)
    assert len(ex.nets) == 1
    v = [x for x in rules.check(fl, ex) if x.rule == "min_space"]
    assert v and {x.a for x in v} >= {arm_a, arm_b}, v
    assert abs(v[0].value_um - 0.10) < 1e-9
    # fill the notch: the same geometry is one convex polygon, no violation
    moves.add_rect_dbu(fl, li, (300, 200, 400, 1000), "t/u")
    ex = extract.extract(fl, T)
    assert not [x for x in rules.check(fl, ex) if x.rule == "min_space"]
    # a slab decomposition (three stacked rects, none touching the far one) is fine too
    fl2 = g.FlatLayout(dbu_um=0.001, top="t", rects=[])
    for y in (0, 100, 200):
        moves.add_rect_dbu(fl2, li, (0, y, 1000, y + 100), "t/u")
    ex2 = extract.extract(fl2, T)
    assert not [x for x in rules.check(fl2, ex2) if x.rule == "min_space"]
    # a separate same-net island 0.05 um from the U (joined elsewhere by met1 is not
    # modelled here, so it is its own net -- different-net spacing still flags it)
    moves.add_rect_dbu(fl, li, (1050, 0, 1400, 1000), "t/u")
    ex = extract.extract(fl, T)
    assert [x for x in rules.check(fl, ex) if x.rule == "min_space"]


def _bare_row(cells):
    """A one-row DEF of the given (macro, x_um) placements between fillers; returns the FlatLayout."""
    from .. import lefdef
    lib = os.path.expanduser("~/tools/sky130_fd_sc_hd")
    if not os.path.exists(os.path.join(lib, "sky130_fd_sc_hd__fill_8.gds")):
        return None
    comps = " ".join("- u%d sky130_fd_sc_hd__%s + PLACED ( %d 0 ) N ;" % (i, m, int(x * 1000)) for i, (m, x) in enumerate(cells))
    deftext = """VERSION 5.8 ; DESIGN t ; UNITS DISTANCE MICRONS 1000 ; DIEAREA ( 0 0 ) ( 12000 2720 ) ;
COMPONENTS %d ; %s END COMPONENTS
SPECIALNETS 2 ; - VPWR + USE POWER ; - VGND + USE GROUND ; END SPECIALNETS
END DESIGN""" % (len(cells), comps)
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "t.def"), "w").write(deftext)
        lefs = [os.path.join(lib, "sky130_fd_sc_hd.tlef")] + [os.path.join(lib, "sky130_fd_sc_hd__%s.lef" % m) for m in sorted({m for m, _ in cells})]
        return lefdef.def2flat(os.path.join(td, "t.def"), lefs, lib, T)


def test_remove_finger_roundtrip():
    """add_finger then remove_finger on the bare nand2 row gives back the
    original netlist and device sizes, with no new violations."""
    from .. import moves as mv, drc as rules
    fl = _bare_row([("fill_4", 0.0), ("nand2_1", 1.84), ("fill_8", 3.22)])
    if fl is None:
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    ex0 = extract.extract(fl, T)
    sig = ex0.signature(); base = {rules.key(v) for v in rules.check(fl, ex0)}
    sizes0 = sorted((x.kind, round(x.w, 3), x.fingers) for x in ex0.devices)
    devs = sorted([d for d in ex0.devices if d.kind == "p"], key=lambda x: -max(ex0.shapes[g].rect[2] for g in x.gate_ids))
    mv.add_finger(fl, ex0, devs[0], side="high")
    ex1 = extract.extract(fl, T)
    dev = next(x for x in ex1.devices if x.kind == "p" and x.fingers == 2)
    touched = mv.remove_finger(fl, ex1, dev, side="high")
    ex2 = extract.extract(fl, T)
    assert ex2.signature() == sig
    assert sorted((x.kind, round(x.w, 3), x.fingers) for x in ex2.devices) == sizes0, sorted((x.kind, round(x.w, 3), x.fingers) for x in ex2.devices)
    nv = rules.new_violations(fl, ex2, touched, base)
    assert not nv, nv[:3]
    # nothing of the added finger is left: rect count back to the original
    print("  roundtrip: %d rects (original %d)" % (len(fl.rects), len(extract.extract(_bare_row([("fill_4", 0.0), ("nand2_1", 1.84), ("fill_8", 3.22)]), T).shapes) and len(_bare_row([("fill_4", 0.0), ("nand2_1", 1.84), ("fill_8", 3.22)]).rects)))


def test_remove_finger_stock_buf4():
    """A stock buf_4 loses one PMOS and one NMOS finger of its output stage:
    same netlist, W down by one finger each, no new violations."""
    from .. import moves as mv, drc as rules
    fl = _bare_row([("fill_4", 0.0), ("buf_4", 1.84), ("fill_8", 4.60)])
    if fl is None:
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    ex0 = extract.extract(fl, T)
    sig = ex0.signature(); base = {rules.key(v) for v in rules.check(fl, ex0)}
    before = {(x.kind, x.fingers): round(x.w, 3) for x in ex0.devices}
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        dev = max((x for x in ex.devices if x.kind == kind), key=lambda x: x.fingers)
        f0 = dev.fingers
        touched = mv.remove_finger(fl, ex, dev, side="high")
        ex2 = extract.extract(fl, T)
        assert ex2.signature() == sig, kind
        d2 = max((x for x in ex2.devices if x.kind == kind), key=lambda x: x.fingers)
        assert d2.fingers == f0 - 1, (kind, f0, d2.fingers)
        nv = rules.new_violations(fl, ex2, touched, base)
        assert not nv, (kind, nv[:3])
        base = {rules.key(v) for v in rules.check(fl, ex2)}
    ex2 = extract.extract(fl, T)
    print("  buf_4: %s -> %s" % (sorted(before.items()), sorted({(x.kind, x.fingers): round(x.w, 3) for x in ex2.devices}.items())))


def test_drive_model_liberty():
    """The Liberty reader gets inv_1/inv_4/nand2_1 delay tables; the slope
    fits give R*W consistent with tech.SKY130.drive within 10% for the
    inverters, and nand2's NMOS stack costs the fitted stack factor, not 2."""
    from .. import drive
    lib_path = os.path.expanduser("~/tools/orfs-sky130hd/sky130_fd_sc_hd__tt_025C_1v80.lib")
    if not os.path.exists(lib_path):
        print("  (liberty not found, skipped)"); return
    P = "sky130_fd_sc_hd__"
    lib = drive.read_liberty(lib_path, [P + "inv_1", P + "inv_4", P + "nand2_1"])
    assert len(lib) == 3
    dm = T.drive
    for name, wp, wn in (("inv_1", 1.0, 0.65), ("inv_4", 4.0, 2.6)):
        arc = lib[P + name].output().arcs[0]
        fr = drive.edge_fit(arc, "rise", 50.0); ff = drive.edge_fit(arc, "fall", 50.0)
        assert abs(fr.r_ohm / dm.r_rise(wp) - 1) < 0.10, (name, fr.r_ohm, dm.r_rise(wp))
        assert abs(ff.r_ohm / dm.r_fall(wn) - 1) < 0.10, (name, ff.r_ohm, dm.r_fall(wn))
    nand = lib[P + "nand2_1"].output()
    arc = [a for a in nand.arcs if a.related_pin == "A"][0]
    ff = drive.edge_fit(arc, "fall", 50.0)
    assert abs(ff.r_ohm / dm.r_fall(0.65, stack=2) - 1) < 0.12, (ff.r_ohm, dm.r_fall(0.65, stack=2))
    assert ff.r_ohm / dm.r_fall(0.65) < 1.8                      # a stack of two is not twice
    # the slew model reproduces inv_1's table: 50% delay at (slew, load) points within 10%,
    # output transition within 15%
    a1 = lib[P + "inv_1"].output().arcs[0]
    for si, li in ((1, 3), (3, 3), (3, 5), (4, 2)):
        s_in, c = a1.slews[si], a1.loads[li]
        for edge, w, tab, trt in (("rise", 1.0, a1.rise, a1.rise_tr), ("fall", 0.65, a1.fall, a1.fall_tr)):
            r = dm.r_rise(w) if edge == "rise" else dm.r_fall(w)
            d, tr = dm.stage(edge, w, c, r * c / 1000.0, s_in)
            assert abs(d / tab[si][li] - 1) < 0.10, (edge, s_in, c, d, tab[si][li])
            assert abs(tr / trt[si][li] - 1) < 0.15, (edge, s_in, c, tr, trt[si][li])
    print("  inv_1 R_rise %.0f / R_fall %.0f ohm; nand2 A fall %.0f (stack %.2f)" % (
        drive.edge_fit(lib[P + "inv_1"].output().arcs[0], "rise", 50.0).r_ohm,
        drive.edge_fit(lib[P + "inv_1"].output().arcs[0], "fall", 50.0).r_ohm, ff.r_ohm, ff.r_ohm / dm.r_fall(0.65)))


def test_move_pr_wire():
    """A P&R-style wall of another net fills the field gap on met1 and met2,
    with li walls beside the cell and sealed rows above and below, so the far
    gate of the mirrored NMOS stack has no path at all.  The router then moves
    the wall: cuts it around the connection and reconnects the pieces.  The
    stack goes in, the wall's net stays one net, nothing new is violated."""
    from .. import moves as mv, drc as rules
    fl = _bare_row([("fill_4", 0.0), ("nand2_1", 1.84), ("fill_8", 3.22)])
    if fl is None:
        print("  (sky130_fd_sc_hd cells not found, skipped)"); return
    L = T.layers
    for lay, (y0, y1) in (("met1", (1020, 1470)), ("met2", (1020, 1470)),
                          ("li", (-2500, -430)), ("met1", (-2500, -420)), ("met2", (-2500, -420)),
                          ("li", (2780, 5000)), ("met1", (2800, 5000)), ("met2", (2800, 5000))):
        mv.add_rect_dbu(fl, L[lay], (500, y0, 6000, y1), "t/net:blk")
    mv.add_rect_dbu(fl, L["via1"], (610, 1070, 760, 1220), "t/net:blk")
    for x0, x1 in ((1000, 1760), (4250, 4420)):
        mv.add_rect_dbu(fl, L["li"], (x0, -400, x1, 2780), "t/net:blk")
    ex = extract.extract(fl, T); sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    blk_nets = lambda e: {e.net_of_shape[i] for i, sh in enumerate(e.shapes) if sh.src >= 0 and fl.rects[sh.src].prov == "t/net:blk"}
    n_blk = len(blk_nets(ex))
    for kind in ("p", "n"):
        ex = extract.extract(fl, T)
        devs = sorted([d for d in ex.devices if d.kind == kind], key=lambda x: -max(ex.shapes[g].rect[2] for g in x.gate_ids))
        touched = mv.add_finger(fl, ex, devs[0], side="high")
        ex2 = extract.extract(fl, T)
        assert ex2.signature() == sig, kind
        assert len(blk_nets(ex2)) == n_blk, (kind, n_blk, len(blk_nets(ex2)))
        nv = rules.new_violations(fl, ex2, touched, base)
        assert not nv, (kind, nv[:3])
        base = {rules.key(v) for v in rules.check(fl, ex2)}
    rr = mv.LAST_PLAN_TALLY.get("reroute")
    assert isinstance(rr, dict) and rr.get("moved"), mv.LAST_PLAN_TALLY
    print("  moved %d P&R wire(s) to make room: %s" % (len(rr["moved"]), rr["moved"]))



if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:                      # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
