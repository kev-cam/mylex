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


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print("PASS", name)
            except Exception as e:                      # noqa: BLE001
                fails += 1; print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
