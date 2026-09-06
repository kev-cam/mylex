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


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:                      # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
