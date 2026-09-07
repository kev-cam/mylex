#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""layopt L2 on a real DEF: def2flat vs KLayout's own DEF reader, both extracted.

  layopt : def2flat(DEF, tech LEF + cell LEF, merged cell GDS) -> extract -> SPICE
  KLayout: read the DEF with LEF + macro_layout_files (real cell geometry) ->
           flat GDS -> KLayout LayoutToNetlist (kestrel's extract.py recipe) -> SPICE
  compare: layopt.compare (W/L multiset, degree histogram, isomorphism)

Usage: l2_real_def.py design.def [--lef tech.lef,cells.lef] [--gds merged.gds] [--out DIR]
Defaults: ~/tools/orfs-sky130hd/{sky130_fd_sc_hd.tlef,sky130_fd_sc_hd_merged.lef,sky130_fd_sc_hd.gds}
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from layopt import compare, extract, gds, lefdef, rc, tech      # noqa: E402

ORFS = os.path.expanduser("~/tools/orfs-sky130hd")
KESTREL = os.environ.get("KESTREL_DIR", "/usr/local/src/kestrel")
T = tech.SKY130


def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


SKY130_LEFDEF_MAP = {"nwell": (64, 20), "pwell": (64, 44), "li1": (67, 20), "mcon": (67, 44), "met1": (68, 20),
                     "via": (68, 44), "met2": (69, 20), "via2": (69, 44), "met3": (70, 20), "via3": (70, 44),
                     "met4": (71, 20), "via4": (71, 44), "met5": (72, 20)}


def write_lefdef_map(path):
    """KLayout/Cadence-style LEF/DEF layer map: routing, special routing, vias,
    pins and LEF pins of each layer onto the sky130 drawing (layer, datatype)."""
    with open(path, "w") as fh:
        for name, (l, d) in SKY130_LEFDEF_MAP.items():
            for purpose in ("NET", "SPNET", "VIA", "PIN", "LEFPIN", "LEFOBS"):
                fh.write("%s %s %d %d\n" % (name, purpose, l, d))
    return path


def klayout_flat_gds(def_path, lefs, gds_lib, out_gds):
    import klayout.db as kdb
    opt = kdb.LoadLayoutOptions()
    cfg = opt.lefdef_config
    cfg.lef_files = lefs
    cfg.macro_layout_files = [gds_lib]
    cfg.macro_resolution_mode = 2                 # always take the real cell geometry from the GDS
    cfg.map_file = write_lefdef_map(os.path.splitext(out_gds)[0] + ".lefdef.map")
    cfg.read_lef_with_def = True
    cfg.produce_routing = True
    cfg.produce_special_routing = True
    cfg.produce_pins = False
    cfg.produce_obstructions = False
    cfg.produce_blockages = False
    cfg.produce_regions = False
    cfg.produce_placement_blockages = False
    cfg.produce_cell_outlines = False
    cfg.produce_via_geometry = True
    ly = kdb.Layout()
    ly.read(def_path, opt)
    top = ly.top_cells()[0]
    top.flatten(True)
    # keep only the sky130 drawing layers we extract (drop LEF/DEF marker layers)
    keep = set(T.layers.values())
    for li in list(ly.layer_indexes()):
        info = ly.get_info(li)
        if (info.layer, info.datatype) not in keep:
            ly.delete_layer(li)
    ly.write(out_gds)
    return top.name


def klayout_extract(gds_path, cir_path):
    """KLayout LayoutToNetlist with the FULL sky130 stack (li1 .. met5) -- kestrel's
    extract.py stops at met3, which fragments a power grid routed on met4/met5."""
    import klayout.db as kdb
    ly = kdb.Layout(); ly.read(gds_path)
    tc = ly.top_cells()[0]
    l2n = kdb.LayoutToNetlist(kdb.RecursiveShapeIterator(ly, tc, []))
    L = {}
    for name, (ln, dt) in T.layers.items():
        if name == "text":
            continue
        li = ly.find_layer(ln, dt)
        L[name] = l2n.make_layer(li, name) if li is not None else l2n.make_layer(name)
    gate = L["poly"] & L["diff"]; sd = L["diff"] - L["poly"]
    nsd = (sd & L["nsdm"]) - L["nwell"]; psd = (sd & L["psdm"]) & L["nwell"]
    ngate = gate - L["nwell"]; pgate = gate & L["nwell"]
    l2n.extract_devices(kdb.DeviceExtractorMOS3Transistor(T.nfet_model), {"SD": nsd, "G": ngate, "P": ngate})
    l2n.extract_devices(kdb.DeviceExtractorMOS3Transistor(T.pfet_model), {"SD": psd, "G": pgate, "P": pgate})
    for name in [T.poly] + list(T.routing) + [cut for _, cut, _ in T.vias] + [T.diff_contact]:
        if name in L:
            l2n.connect(L[name])
    for r in (nsd, psd, ngate, pgate):
        l2n.connect(r)
    l2n.connect(ngate, L["poly"]); l2n.connect(pgate, L["poly"])
    l2n.connect(nsd, L["licon"]); l2n.connect(psd, L["licon"]); l2n.connect(L["poly"], L["licon"])
    l2n.connect(L["licon"], L["li"])
    for lo, cut, up in T.vias:
        if cut in L and lo in L and up in L:
            l2n.connect(L[lo], L[cut]); l2n.connect(L[cut], L[up])
    l2n.extract_netlist()
    nl = l2n.netlist(); nl.combine_devices(); nl.purge()
    nl.write(cir_path, kdb.NetlistSpiceWriter())


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    def_path = sys.argv[1]
    lefs = arg("--lef", "%s/sky130_fd_sc_hd.tlef,%s/sky130_fd_sc_hd_merged.lef" % (ORFS, ORFS)).split(",")
    gds_lib = arg("--gds", ORFS + "/sky130_fd_sc_hd.gds")
    out = arg("--out", os.path.dirname(os.path.abspath(def_path)))
    base = os.path.splitext(os.path.basename(def_path))[0]
    t0 = time.time()
    fl = lefdef.def2flat(def_path, lefs, "", T, gds_lib=gds_lib)
    ex = extract.extract(fl, T)
    t1 = time.time()
    insts = {r.prov.split("/")[1] for r in fl.rects if r.prov.count("/") >= 2 and not r.prov.split("/")[1].startswith(("net:", "pin:"))}
    print("== layopt def2flat: %d rects (%d instances), extract: %d shapes, %d nets, %d devices (%d n / %d p) in %.1fs" % (
        len(fl.rects), len(insts), len(ex.shapes), len(ex.nets), len(ex.devices),
        sum(d.kind == "n" for d in ex.devices), sum(d.kind == "p" for d in ex.devices), t1 - t0))
    named = [n for n in ex.nets.values() if not n.name.isdigit()]
    print("   named nets %d (e.g. %s); supply nets: %s" % (len(named), [n.name for n in named[:6]],
          {n.name: len(n.devices) for n in named if n.name in T.supply_names or n.name in ("VDD", "VSS")}))
    extract.write_spice(ex, os.path.join(out, base + ".layopt.cir"))
    gds.write_flat(fl, os.path.join(out, base + ".layopt.gds"))
    nets = rc.all_nets_rc(ex, with_segments=True)
    rc.write_spef(nets, os.path.join(out, base + ".layopt.spef"), base)
    print("   wrote %s.layopt.{cir,gds,spef}; total C %.1f fF over %d nets" % (base, sum(n.c_fF for n in nets), len(nets)))
    # KLayout side
    kl_gds = os.path.join(out, base + ".klayout.gds")
    top = klayout_flat_gds(def_path, lefs, gds_lib, kl_gds)
    kl_cir = os.path.join(out, base + ".klayout.cir")
    klayout_extract(kl_gds, kl_cir)
    print("== KLayout: DEF+LEF+macro GDS -> flat GDS (%s) -> LayoutToNetlist -> %s" % (top, os.path.basename(kl_cir)))
    res = compare.compare_to_reference(ex, kl_cir)
    for k in ("ref_devices", "our_devices", "wl_match", "degree_hist_match", "isomorphic", "area_perim_match"):
        print("   %-18s %s" % (k, res[k]))
    if res["wl_only_ours"] or res["wl_only_ref"]:
        print("   W/L only in layopt: %s\n   W/L only in KLayout: %s" % (dict(list(res["wl_only_ours"].items())[:5]), dict(list(res["wl_only_ref"].items())[:5])))
    ok = res["wl_match"] and res["isomorphic"] and res["degree_hist_match"]
    print("RESULT", "MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
