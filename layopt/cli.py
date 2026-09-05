# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt command line: extract | rc | compare | flatten | resize."""
import argparse
import sys

from . import compare, extract, gds, moves, rc, tech


def _load(args):
    lib = gds.read(args.gds)
    fl = gds.flatten(lib, args.top)
    labels = {}
    for s in args.label or []:
        name, rest = s.split("=", 1)
        layer, x, y = rest.split(",")
        labels[name] = (layer, float(x), float(y))
    return fl, extract.extract(fl, tech.get(args.tech), labels or None)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="layopt", description=__doc__)
    ap.add_argument("--tech", default="sky130")
    ap.add_argument("--top")
    ap.add_argument("--label", action="append", help="NAME=layer,x_um,y_um  name the net at a point")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract", help="flatten + extract; write SPICE"); p.add_argument("gds"); p.add_argument("-o", "--output")
    p = sub.add_parser("rc", help="per-net RC; write SPEF"); p.add_argument("gds"); p.add_argument("-o", "--output"); p.add_argument("--top-n", type=int, default=10)
    p = sub.add_parser("compare", help="compare extraction to a reference SPICE netlist"); p.add_argument("gds"); p.add_argument("ref")
    p = sub.add_parser("flatten", help="write the dissolved (flat) GDS"); p.add_argument("gds"); p.add_argument("-o", "--output", required=True)
    p = sub.add_parser("render", help="SVG of a window (um): x0 y0 x1 y1"); p.add_argument("gds"); p.add_argument("window", nargs=4, type=float); p.add_argument("-o", "--output", required=True)
    p = sub.add_parser("resize", help="resize a device W by provenance substring and write GDS")
    p.add_argument("gds"); p.add_argument("device"); p.add_argument("width_um", type=float); p.add_argument("-o", "--output", required=True)
    args = ap.parse_args(argv)

    fl, ex = _load(args)
    if args.cmd == "extract":
        print("top %s: %d shapes, %d nets, %d devices (%d n / %d p)" % (
            ex.top, len(ex.shapes), len(ex.nets), len(ex.devices),
            sum(d.kind == "n" for d in ex.devices), sum(d.kind == "p" for d in ex.devices)))
        if args.output:
            extract.write_spice(ex, args.output); print("wrote", args.output)
    elif args.cmd == "rc":
        nets = rc.all_nets_rc(ex, with_segments=True)
        print("%d nets, total C %.1f fF, total lumped R %.1f kohm" % (
            len(nets), sum(n.c_fF for n in nets), sum(n.r_ohm for n in nets) / 1e3))
        for n in sorted(nets, key=lambda n: -n.c_fF)[:args.top_n]:
            print("  net %-6s C %7.2f fF  R %8.1f ohm  %s" % (n.name, n.c_fF, n.r_ohm,
                  " ".join("%s=%.1f" % kv for kv in sorted(n.per_layer_c.items()))))
        if args.output:
            rc.write_spef(nets, args.output, ex.top); print("wrote", args.output)
    elif args.cmd == "compare":
        r = compare.compare_to_reference(ex, args.ref)
        for k, v in r.items():
            if isinstance(v, dict):
                v = dict(list(v.items())[:5])
            print("%-20s %s" % (k, v))
        ok = r["wl_match"] and r["isomorphic"] and r["degree_hist_match"]
        print("RESULT", "MATCH" if ok else "MISMATCH")
        return 0 if ok else 1
    elif args.cmd == "flatten":
        gds.write_flat(fl, args.output); print("wrote", args.output, len(fl.rects), "rects")
    elif args.cmd == "render":
        from . import render
        render.svg(fl, ex.tech, tuple(args.window), args.output); print("wrote", args.output)
    elif args.cmd == "resize":
        devs = [d for d in ex.devices if args.device in d.prov]
        if len(devs) != 1:
            sys.exit("device %r matches %d devices" % (args.device, len(devs)))
        sig0 = ex.signature()
        from . import drc
        baseline = {drc.key(v) for v in drc.check(fl, ex)}
        touched = moves.resize_device_w(fl, ex, devs[0], args.width_um)
        ex2 = extract.extract(fl, ex.tech)
        viol = drc.new_violations(fl, ex2, touched, baseline)
        d2 = [d for d in ex2.devices if args.device in d.prov][0]
        print("%s: W %.3f -> %.3f um, %d rects touched, topology %s, %d new rule violations" % (
            devs[0].prov, devs[0].w, d2.w, len(touched), "preserved" if ex2.signature() == sig0 else "CHANGED", len(viol)))
        for v in viol[:10]:
            print("  ", v)
        gds.write_flat(fl, args.output); print("wrote", args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
