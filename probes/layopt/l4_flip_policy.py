# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""The placer-side flip policy: which orientation (N or mirrored) each cell of
a row should take so that abutting cells meet source to source on both
strips -- the boundaries the dissolve can close.

    python3 probes/layopt/l4_flip_policy.py [--def path]

For every macro the outer S/D region nets on its left and right (N
orientation) come from layopt's extraction of the cell alone; mirroring
swaps them.  Per row (cells in x order, fillers and taps set aside as a
packed row would), a dynamic programme over the two orientations of each
cell maximises the number of strips matched across boundaries.  The exact
slide each chosen boundary allows is measured on a two-cell layout of that
pair (`_merge_plan`, cached per macro pair and orientations).  Reports the
placement as it is, the policy's result, and what a packed, flipped,
dissolved row would give back.  Evidence: evidence/l4_flip_policy.log.
"""
import os
import sys
import tempfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
sys.path.insert(0, HERE)
from layopt import extract, lefdef, moves as mv, tech as techmod  # noqa: E402

T = techmod.SKY130
ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
DEF = sys.argv[sys.argv.index("--def") + 1] if "--def" in sys.argv else os.path.join(HERE, "gcd", "gcd.def")
P = "sky130_fd_sc_hd__"
LEFS = [os.path.join(ORFS, "sky130_fd_sc_hd.tlef"), os.path.join(ORFS, "sky130_fd_sc_hd_merged.lef")]
GDS = os.path.join(ORFS, "sky130_fd_sc_hd.gds")
MIRROR = {"N": "FN", "FN": "N", "FS": "S", "S": "FS"}


# the policy's core lives in layopt/placer.py (Faces: outer nets, orientation faces,
# strip matching, exact slides); these names keep the probe's text below unchanged
from layopt import placer as _placer   # noqa: E402

_F = _placer.Faces(LEFS, GDS, T, cache_path=os.path.join(HERE, "evidence", "pair_slides.json"))
layout_of = _F.layout_of
outer_nets = _F.outer_nets
faces = _F.faces
match = _F.match
exact_slide = _F.exact_slide
_pair_cache = _F._slide


def main():
    d = lefdef.read_def(DEF)
    comps = [c for c in d.components if c.placed]
    is_filler = lambda c: any(t in c.macro for t in ("fill", "tap", "decap"))
    rows = defaultdict(list)
    for c in comps:
        rows[c.y].append(c)
    logic_rows = {y: sorted([c for c in cs if not is_filler(c)], key=lambda c: c.x) for y, cs in rows.items()}
    n_logic = sum(len(v) for v in logic_rows.values())
    macros = sorted({c.macro for cs in logic_rows.values() for c in cs})
    print("== %s: %d rows, %d logic cells, %d macros" % (os.path.basename(DEF), len(rows), n_logic, len(macros)))
    for m in macros:
        outer_nets(m)
    # as placed: boundaries between adjacent logic cells (any gap) and their strip matches
    as_is = Counter(); adj = 0
    for y, cs in logic_rows.items():
        for a, b in zip(cs, cs[1:]):
            adj += 1
            as_is[match(faces(a.macro, a.orient)[1], faces(b.macro, b.orient)[0])] += 1
    print("   as placed (fillers set aside, %d logic|logic neighbours): strips matched %s" % (adj, dict(sorted(as_is.items()))))
    # the policy: per row, orientations maximising matched strips (each cell N or its mirror)
    policy = Counter(); flips = 0; chosen = []
    for y, cs in logic_rows.items():
        if not cs:
            continue
        opts = [(c.orient, MIRROR.get(c.orient, c.orient)) for c in cs]
        best = [{o: (0, None) for o in opts[0]}]
        for i in range(1, len(cs)):
            cur = {}
            for o in opts[i]:
                cands = []
                for po, (score, _) in best[-1].items():
                    cands.append((score + match(faces(cs[i - 1].macro, po)[1], faces(cs[i].macro, o)[0]), po))
                cur[o] = max(cands)
            best.append(cur)
        o = max(best[-1], key=lambda k: best[-1][k][0])
        seq = [o]
        for i in range(len(cs) - 1, 0, -1):
            seq.append(best[i][seq[-1]][1])
        seq.reverse()
        for c, o in zip(cs, seq):
            if o != c.orient:
                flips += 1
        for i in range(1, len(cs)):
            m = match(faces(cs[i - 1].macro, seq[i - 1])[1], faces(cs[i].macro, seq[i])[0])
            policy[m] += 1
            if m:
                chosen.append((cs[i - 1].macro, seq[i - 1], cs[i].macro, seq[i], m))
    print("   with the flip policy (%d of %d cells mirrored): strips matched %s" % (flips, n_logic, dict(sorted(policy.items()))))
    # exact slides for the chosen boundaries, by pair type
    tot = 0.0; kinds = Counter(); lims = Counter()
    for ma, oa, mb, ob, m in chosen:
        sl, lim, nets = exact_slide(ma, oa, mb, ob)
        tot += sl; kinds["%d strips" % m] += 1
        lims[lim.split(" [")[0][:40]] += 1
    width = 0.0
    lef = lefdef.Lef()
    for f in LEFS:
        lefdef.read_lef(f, lef)
    for cs in logic_rows.values():
        width += sum(lef.macros[c.macro].size[0] for c in cs)
    print("   packed, flipped, dissolved: %d shared boundaries give back %.2f um = %.1f%% of %.1f um of logic cell width (%d two-cell layouts measured)" % (
        len(chosen), tot, 100 * tot / width if width else 0, width, len(_pair_cache)))
    print("   what bounds the slides: %s" % lims.most_common(5))
    top = sorted(_pair_cache.items(), key=lambda kv: -kv[1][0])[:6]
    for (ma, oa, mb, ob), (sl, lim, nets) in top:
        print("      %s(%s) | %s(%s): %.3f um (%s)" % (ma.replace(P, ""), oa, mb.replace(P, ""), ob, sl, "+".join(nets)))
    # the policy applied: the row with the most shared boundaries, packed (fillers out),
    # flipped as chosen, every shared boundary dissolved with the rest of the row sliding
    from layopt import drc as rules, gds as gdsmod, compare
    from l2_real_def import klayout_extract
    best_row = None
    for y, cs in logic_rows.items():
        if len(cs) < 2:
            continue
        opts = [(c.orient, MIRROR.get(c.orient, c.orient)) for c in cs]
        dp = [{o: (0, None) for o in opts[0]}]
        for i in range(1, len(cs)):
            cur = {}
            for o in opts[i]:
                cur[o] = max((sc + match(faces(cs[i - 1].macro, po)[1], faces(cs[i].macro, o)[0]), po) for po, (sc, _) in dp[-1].items())
            dp.append(cur)
        o = max(dp[-1], key=lambda k: dp[-1][k][0]); seq = [o]
        for i in range(len(cs) - 1, 0, -1):
            seq.append(dp[i][seq[-1]][1])
        seq.reverse()
        score = dp[-1][o][0]
        if best_row is None or score > best_row[0]:
            best_row = (score, y, cs, seq)
    score, y, cs, seq = best_row
    cells = []; x = 1.84
    for c, o in zip(cs, seq):
        cells.append((c.macro, x, o)); x += lef.macros[c.macro].size[0]
    row = [(P + "fill_4", 0.0, "N")] + cells + [(P + "fill_8", x, "N")]
    fl = layout_of(row)
    ex = extract.extract(fl, T); sig = ex.signature(); base = {rules.key(v) for v in rules.check(fl, ex)}
    insts = [next(r.prov for r in fl.rects if "/u%d/" % (i + 1) in r.prov) for i in range(len(cells))]
    print("== the policy applied to row y=%d (%d cells, %d strips matched across %d boundaries), packed and flipped:" % (y, len(cs), score, len(cs) - 1))
    total = 0.0; n_ok = 0
    for a, b in zip(insts, insts[1:]):
        ex = extract.extract(fl, T)
        try:
            d0, lim, nets = mv._merge_plan(fl, ex, a, b)[:3]
        except mv.MoveError as e:
            continue
        if d0 < 50:
            continue
        try:
            t = mv.merge_boundary(fl, ex, a, b, shift_row=True)
        except mv.MoveError as e:
            print("   %s|%s: refused -- %s" % (a.split("/")[2].replace(P, ""), b.split("/")[2].replace(P, ""), str(e)[:80])); continue
        ex2 = extract.extract(fl, T)
        nv = rules.new_violations(fl, ex2, t, base)
        ok = ex2.signature() == sig and not nv
        print("   %s|%s (%s): slid %.3f um -> topology %s, %d new violations" % (a.split("/")[2].replace(P, ""), b.split("/")[2].replace(P, ""), "+".join(nets),
                                                                                    mv.LAST_MERGE_DELTA[0] / 1000, "same" if ex2.signature() == sig else "CHANGED", len(nv)))
        if ok:
            total += mv.LAST_MERGE_DELTA[0] / 1000; n_ok += 1; base = {rules.key(v) for v in rules.check(fl, ex2)}
        else:
            for v in nv[:2]:
                print("      %s" % str(v)[:120])
    ex2 = extract.extract(fl, T)
    out = os.path.join(HERE, "evidence", "gcd_row_flipped_dissolved.gds"); gdsmod.write_flat(fl, out)
    cir = out.replace(".gds", "_klayout.cir"); klayout_extract(out, cir)
    res = compare.compare_to_reference(ex2, cir)
    width = sum(lef.macros[c.macro].size[0] for c in cs)
    print("   row: %d boundaries dissolved, %.2f um given back of %.2f um of cells (%.1f%%); KLayout devices %d/%d, W/L %s, isomorphic %s" % (
        n_ok, total, width, 100 * total / width, res["ref_devices"], res["our_devices"], res["wl_match"], res["isomorphic"]))


if __name__ == "__main__":
    main()
