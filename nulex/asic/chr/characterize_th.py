#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Characterize the native TH cells (SG13G2 domain) -> Liberty NLDM timing.

Two paths:

  --spice   the GOLD path: transistor-level Xyce transient sweeps of the native
            cells (ldx/asic/cells/th22.sp, th_gates.sp) with the SG13G2 PSP103
            model card. For each (input slew x output load) grid point it drives
            a ramp, measures the input->output propagation delay and the output
            transition, and (for the C-element) the set/reset switching plus the
            hold — then assembles NLDM cell_rise/fall + transition tables.
            REQUIRES a Xyce with PSP103 (the ldx flow used a PyMS-built
            psp103_sg13g2.so plugin / a custom Xyce-8). The stock Xyce here has
            no PSP103, so this path reports the missing device and stops.

  --from-lib <sg13g2_stdcell.lib>
            derive the TH-cell Liberty from IHP's silicon-characterized SG13G2
            standard-cell library (the comb TH cells realized on it: th22=and2,
            th12=or2, th13=or3, th33=and3, th44=and4; th23=majority via a22oi).
            Real SG13G2 timing at the lib's corner (1.2V/25C), available now.

Usage: characterize_th.py --from-lib <stdcell.lib> [out.lib]
       characterize_th.py --spice [out.lib] [--cell thNN]
  --cell thNN   characterize just one cell (for parallel per-cell runs).
"""
import os, re, subprocess, sys

CELLS = "/usr/local/src/ldx/asic/cells"
MODEL = "/usr/local/src/kestrel/sim/models/sg13g2_psp103_tt.lib"
# PSP103 now binds via the PyMS-fixed Xyce (.hdl JIT); override XYCE to point at it.
XYCE = os.environ.get("XYCE", "/usr/local/src/xyce-build/src/Xyce")
PSP103_VA = "/usr/local/share/xyce/verilog-a/psp103/psp103.va"
# comb TH cell -> the SG13G2 std cell realizing the same function (single-cell map)
TH_MAP = {"th22": "and2_1", "th12": "or2_1", "th13": "or3_1", "th33": "and3_1", "th44": "and4_1"}
PIN_MAP = {"A": "a", "B": "b", "C": "c", "D": "d", "X": "y"}

# --- gold --spice NLDM grid + cell set ---------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
SUP = os.path.join(HERE, "..", "..", "lib", "th_cells_sg13g2.sp")   # th13/th14
INCLUDES = [os.path.join(CELLS, "th22.sp"), os.path.join(CELLS, "th_gates.sp"), SUP]
VDD = 1.2
# input transition (slew) [s] and output load [F] axes of the NLDM tables
SLEWS = [20e-12, 50e-12, 100e-12, 200e-12, 400e-12]
LOADS = [1e-15, 5e-15, 10e-15, 20e-15, 50e-15]
# each native transistor TH cell + its input pins (port order is <inputs> Y VDD VSS)
SPICE_CELLS = [
    ("th22",   ["A", "B"]),        # 2-of-2 Muller C-element
    ("th12",   ["A", "B"]),        # 1-of-2 (OR2)
    ("th13",   ["A", "B", "C"]),   # 1-of-3 (OR3)
    ("th14",   ["A", "B", "C", "D"]),   # 1-of-4 (OR4)
    ("th23",   ["A", "B", "C"]),   # 2-of-3 majority
    ("th33",   ["A", "B", "C"]),   # 3-of-3 (AND3)
    ("th34w2", ["A", "B", "C", "D"]),   # weighted 3-of-4 (A weight 2)
]
# estimated input pin capacitance [pf] (a placeholder; delay/transition are the
# measured gold, Cin is refined from --from-lib or a dedicated Q-sweep later)
CIN_PF = 0.001


def spice_probe():
    """Confirm the SG13G2 PSP103 device is usable in this Xyce (else the gold
    transistor characterization cannot run here). The PyMS-fixed Xyce binds
    PSP103 via .hdl JIT, so the probe includes the psp103.va .hdl line."""
    deck = "/tmp/_psp_probe.cir"
    open(deck, "w").write('.hdl "%s"\n.include "%s"\nM1 d g 0 0 sg13g2_nmos W=1u L=0.13u\n'
                          'Vg g 0 1.2\nVd d 0 0.6\n.op\n.end\n' % (PSP103_VA, MODEL))
    try:
        r = subprocess.run([XYCE, deck], capture_output=True, text=True, timeout=420)
    except Exception:
        return False
    return "End of Xyce" in r.stdout and "nrecognized" not in r.stdout \
        and "rror" not in r.stdout.split("Total")[0]


def _deck(cell, pins, arc, wd):
    """Build a .step (slew x load) transient deck for one (cell, arc). arc='set'
    drives the inputs 0->VDD together (rail bundle -> Y rises); 'reset' drives
    VDD->0 (-> Y falls). Both cross every threshold gate's switch point."""
    L = ["* %s %s-arc NLDM sweep" % (cell, arc),
         '.hdl "%s"' % PSP103_VA, '.include "%s"' % MODEL]
    L += ['.include "%s"' % inc for inc in INCLUDES]
    L += [".param CL=1f", ".param TR=50p", "Vdd VDD 0 %g" % VDD, "Vss VSS 0 0"]
    for i, p in enumerate(pins):
        if arc == "set":
            L.append("V%d %s 0 PWL(0 0 2n 0 '2n+TR' %g)" % (i, p, VDD))
        else:
            L.append("V%d %s 0 PWL(0 %g 2n %g '2n+TR' 0)" % (i, p, VDD, VDD))
    L.append("X1 %s Y VDD VSS %s" % (" ".join(pins), cell))
    L.append("Cl Y VSS {CL}")
    L.append(".tran 2p 8n")
    edge, e2 = ("RISE", "RISE") if arc == "set" else ("FALL", "FALL")
    lo, hi = ("0.24", "0.96") if arc == "set" else ("0.96", "0.24")
    L.append(".measure tran td TRIG v(%s) VAL=0.6 %s=1 TARG v(Y) VAL=0.6 %s=1" % (pins[0], edge, e2))
    L.append(".measure tran ts TRIG v(Y) VAL=%s %s=1 TARG v(Y) VAL=%s %s=1" % (lo, edge, hi, e2))
    L.append(".step TR LIST " + " ".join("%gp" % (s * 1e12) for s in SLEWS))    # inner axis
    L.append(".step CL LIST " + " ".join("%gf" % (c * 1e15) for c in LOADS))    # outer axis
    L.append(".end")
    path = os.path.join(wd, "%s_%s.cir" % (cell, arc))
    open(path, "w").write("\n".join(L) + "\n")
    return path


def _mt_dict(path):
    d = {}
    try:
        for ln in open(path):
            m = re.match(r"\s*(\w+)\s*=\s*(\S+)", ln)
            if m:
                try:
                    d[m.group(1).upper()] = float(m.group(2))
                except ValueError:
                    d[m.group(1).upper()] = None
    except OSError:
        pass
    return d


def _read_mt(path):
    d = _mt_dict(path)
    return d.get("TD"), d.get("TS")


def _cin(cell, pins, wd):
    """Per-input-pin capacitance [pf] via a Q-sweep: ramp the target pin 0->VDD
    (other inputs held low), integrate the current delivered INTO it, Cin=|Q|/VDD.
    Includes the Miller charge for cells whose output moves when one input arrives.
    Falls back to the CIN_PF placeholder if a measure fails."""
    caps = {}
    for tgt in pins:
        L = ["* %s Cin(%s) Q-sweep" % (cell, tgt),
             '.hdl "%s"' % PSP103_VA, '.include "%s"' % MODEL]
        L += ['.include "%s"' % inc for inc in INCLUDES]
        L += ["Vdd VDD 0 %g" % VDD, "Vss VSS 0 0"]
        for p in pins:
            if p == tgt:
                L.append("V%s %s 0 PWL(0 0 1n 0 2n %g)" % (p, p, VDD))
            else:
                L.append("V%s %s 0 0" % (p, p))
        L.append("X1 %s Y VDD VSS %s" % (" ".join(pins), cell))
        L.append("Cl Y VSS 2f")
        L.append(".tran 1p 3n")
        L.append(".measure tran q INTEGRAL I(V%s) FROM=1n TO=2n" % tgt)
        L.append(".end")
        cir = os.path.join(wd, "%s_cin_%s.cir" % (cell, tgt))
        open(cir, "w").write("\n".join(L) + "\n")
        subprocess.run([XYCE, cir], capture_output=True, text=True, timeout=600, cwd=wd)
        q = _mt_dict("%s.mt0" % cir).get("Q")
        caps[tgt] = (abs(q) / VDD * 1e12) if q is not None else CIN_PF   # pf
    return caps


def _sweep(cell, pins, arc, wd):
    """Run the (cell, arc) sweep in Xyce; return (delay[slew][load], trans[...])
    in ns, plus a failed-point count. .step nesting: the FIRST .step (TR/slew) is
    the inner loop, the LAST (CL/load) the outer -> mt index = load*nslews+slew."""
    cir = _deck(cell, pins, arc, wd)
    subprocess.run([XYCE, cir], capture_output=True, text=True, timeout=1800,
                   cwd=wd)
    ns, nl = len(SLEWS), len(LOADS)
    dly = [[None] * nl for _ in range(ns)]
    trs = [[None] * nl for _ in range(ns)]
    fails = 0
    for li in range(nl):
        for si in range(ns):
            td, ts = _read_mt("%s.mt%d" % (cir, li * ns + si))
            if td is None or ts is None:
                fails += 1
            dly[si][li] = None if td is None else td * 1e9    # s -> ns
            trs[si][li] = None if ts is None else ts * 1e9
    return dly, trs, fails


def _fill(table):
    """Replace any failed (None) grid point by the nearest valid value in its row
    (then column), so the Liberty table is complete; returns (table, n_filled)."""
    ns = len(table); nl = len(table[0]); n = 0
    for si in range(ns):
        for li in range(nl):
            if table[si][li] is None:
                n += 1
                cand = ([table[si][j] for j in range(nl) if table[si][j] is not None] or
                        [table[i][li] for i in range(ns) if table[i][li] is not None])
                table[si][li] = cand[0] if cand else 0.0
    return table, n


def _lut(name, table):
    rows = ", \\\n      ".join('"%s"' % ", ".join("%.6g" % v for v in row) for row in table)
    return "      %s (NLDM_%dx%d) {\n        values ( %s );\n      }" % (
        name, len(SLEWS), len(LOADS), rows)


def _liberty_cell(cell, pins, rise, fall, cin):
    lp = [p.lower() for p in pins]
    lo = ["  cell (%s) {" % cell,
          "    area : %d;" % len(pins),
          '    cell_footprint : "ncl_th";']
    for p in pins:
        lo += ["    pin (%s) {" % p.lower(), '      direction : "input";',
               "      capacitance : %.6g;" % cin.get(p, CIN_PF), "    }"]
    lo += ["    pin (y) {", '      direction : "output";',
           "      max_capacitance : %g;" % (LOADS[-1] * 1e12),
           "      timing () {",
           '        related_pin : "%s";' % " ".join(lp),
           "        timing_sense : positive_unate;",
           "        timing_type : combinational;",
           _lut("cell_rise", rise[0]),
           _lut("rise_transition", rise[1]),
           _lut("cell_fall", fall[0]),
           _lut("fall_transition", fall[1]),
           "      }", "    }", "  }"]
    return "\n".join(lo)


def _library_header():
    idx1 = ", ".join("%.4g" % (s * 1e9) for s in SLEWS)   # ns
    idx2 = ", ".join("%.4g" % (c * 1e12) for c in LOADS)  # pf
    return "\n".join([
        "library (ncl_th_sg13g2_spice) {",
        '  comment : "nulex native TH-cell NLDM from transistor-level Xyce (PSP103); generated by characterize_th.py --spice";',
        "  delay_model : table_lookup;",
        "  time_unit : \"1ns\";", "  voltage_unit : \"1V\";",
        "  capacitive_load_unit (1,pf);",
        "  nom_voltage : 1.2;  nom_temperature : 25;",
        "  input_threshold_pct_rise : 50;  input_threshold_pct_fall : 50;",
        "  output_threshold_pct_rise : 50;  output_threshold_pct_fall : 50;",
        "  slew_lower_threshold_pct_rise : 20;  slew_upper_threshold_pct_rise : 80;",
        "  slew_lower_threshold_pct_fall : 20;  slew_upper_threshold_pct_fall : 80;",
        "  lu_table_template (NLDM_%dx%d) {" % (len(SLEWS), len(LOADS)),
        "    variable_1 : input_net_transition;",
        "    variable_2 : total_output_net_capacitance;",
        '    index_1 ("%s");' % idx1,
        '    index_2 ("%s");' % idx2,
        "  }",
    ])


def run_spice(outlib, only_cell=None):
    if not os.path.exists(MODEL):
        sys.exit("SG13G2 model card missing: %s" % MODEL)
    if not spice_probe():
        sys.exit("BLOCKED: this Xyce (%s) has no PSP103 device. Point XYCE= at the\n"
                 "PyMS-fixed build (/usr/local/src/xyce-build/src/Xyce, with\n"
                 "PYMS_DIR=/usr/local/share/xyce/PyMS), which binds PSP103 via .hdl JIT.\n"
                 "Meanwhile use: characterize_th.py --from-lib <sg13g2_stdcell.lib>" % XYCE)
    wd = os.path.abspath(outlib) + ".sweep"   # absolute: decks/.mt paths are cwd-independent
    os.makedirs(wd, exist_ok=True)
    cells = [(c, p) for c, p in SPICE_CELLS if only_cell in (None, c)]
    blocks, total_fill = [], 0
    for cell, pins in cells:
        rd, rt, rf = _sweep(cell, pins, "set", wd)
        fd, ft, ff = _sweep(cell, pins, "reset", wd)
        rd, n1 = _fill(rd); rt, n2 = _fill(rt); fd, n3 = _fill(fd); ft, n4 = _fill(ft)
        nfill = n1 + n2 + n3 + n4
        total_fill += nfill
        cap = _cin(cell, pins, wd)     # per-pin Cin [pf] via Q-sweep
        blocks.append(_liberty_cell(cell, pins, (rd, rt), (fd, ft), cap))
        sys.stderr.write("  %-7s set/reset swept (%d filled); set delay %.3f-%.3f ns; Cin %s fF\n"
                         % (cell, nfill, min(min(r) for r in rd), max(max(r) for r in rd),
                            "/".join("%.2f" % (cap[p] * 1e3) for p in pins)))
    text = _library_header() + "\n" + "\n".join(blocks) + "\n}\n"
    open(outlib, "w").write(text)
    print("wrote %s: %d native TH cells, transistor-level NLDM (PSP103, %dx%d slew x load)"
          % (outlib, len(cells), len(SLEWS), len(LOADS)))
    print("  cells: %s" % ", ".join(c for c, _ in cells))
    if total_fill:
        print("  NOTE: %d grid point(s) failed to converge and were nearest-filled." % total_fill)


def cell_block(src, macro):
    i = src.find('cell ("%s")' % macro)
    if i < 0:
        i = src.find("cell (%s)" % macro)
    if i < 0:
        return None
    j = src.find("{", i); depth, k = 1, j + 1
    while depth:
        depth += (src[k] == "{") - (src[k] == "}"); k += 1
    return src[i:k]


def derive_from_lib(stdlib, outlib):
    src = open(stdlib).read()
    header = src[:src.find("\n  cell (") if "\n  cell (" in src else src.find("cell (")]
    prefix = "sg13g2_"
    out = []
    got = []
    for th, sky in TH_MAP.items():
        blk = cell_block(src, prefix + sky) or cell_block(src, sky)
        if blk is None:
            continue
        blk = re.sub(r"\b" + re.escape(prefix + sky) + r"\b", th, blk)
        blk = re.sub(r"\b([ABCDX])\b", lambda g: PIN_MAP[g.group(1)], blk)
        out.append("  " + blk); got.append(th)
    open(outlib, "w").write(header + "\n" + "\n".join(out) + "\n}\n")
    print("wrote %s: %d TH cells with SG13G2-characterized timing (from %s)"
          % (outlib, len(got), os.path.basename(stdlib)))
    print("  cells: %s" % ", ".join(got))
    print("  NOTE: comb cells realized on SG13G2 std cells (real IHP timing). The")
    print("  hysteretic C-element + weighted gates compose these; native-transistor")
    print("  timing (th22.sp) needs the --spice gold path (PSP103).")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--from-lib" in a:
        i = a.index("--from-lib"); stdlib = a[i + 1]
        outlib = a[i + 2] if len(a) > i + 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "th_cells_sg13g2.lib")
        derive_from_lib(stdlib, outlib)
    elif "--spice" in a:
        cell = a[a.index("--cell") + 1] if "--cell" in a else None
        rest = [x for i, x in enumerate(a)
                if x not in ("--spice", "--cell") and (i == 0 or a[i - 1] != "--cell")]
        outlib = rest[0] if rest else os.path.join(HERE, "th_cells_sg13g2_spice.lib")
        run_spice(outlib, only_cell=cell)
    else:
        sys.exit(__doc__)
