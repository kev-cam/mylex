#!/usr/bin/env python3
"""nulex map_ncl_struct — yosys gate netlist (JSON) -> FLAT structural threshold
(TH) gate netlist. Unlike map_ncl.py (which instantiates the behavioral
lib/ncl_gates entities whose TH gates are FUNCTION calls that vanish on
synthesis), this expands each primitive's DIMS template into explicit TH-CELL
instances (lib/th_cells.vhd / blackbox Verilog), so the threshold gates survive
as first-class cells — for physical lowering and for isochronic-fork extraction
(constraints.py then sees th22/th13/... and the dual-rail forks).

MULTIPLE VERSIONS (pick with the flags below):
  --target vhdl     nvc-simulatable VHDL instantiating th_cells entities; the TH
                    architecture binding is chosen with --bind:
      --bind comb   stateless Boolean TH cells (functional / equivalence check)
      --bind qdi    hysteretic C-element TH cells (true delay-insensitive)
  --target verilog  self-contained Verilog with (* blackbox *) TH modules, for
                    `yosys read_verilog; flatten; write_json` -> constraints.py.

Rail convention (lib/ncl): .L = value-1 (t), .H = value-0 (f). DATA0=(L0,H1),
DATA1=(L1,H0), NULL=(0,0). A dual-rail net n{bit} is two std_logic rails.

Usage: map_ncl_struct.py <netlist.json> <top> <out> [--target vhdl|verilog] [--bind comb|qdi]
"""
import json
import sys

# 2-input gates share the 4 TH22 minterms; only the rail collectors differ.
MIN4 = {
    "m11": ("th22", [("a", "L"), ("b", "L")]),
    "m10": ("th22", [("a", "L"), ("b", "H")]),
    "m01": ("th22", [("a", "H"), ("b", "L")]),
    "m00": ("th22", [("a", "H"), ("b", "H")]),
}
G2_RAILS = {
    "$_AND_":  {"L": ["m11"],                "H": ["m10", "m01", "m00"]},
    "$_NAND_": {"L": ["m10", "m01", "m00"],  "H": ["m11"]},
    "$_OR_":   {"L": ["m11", "m10", "m01"],  "H": ["m00"]},
    "$_NOR_":  {"L": ["m00"],                "H": ["m11", "m10", "m01"]},
    "$_XOR_":  {"L": ["m10", "m01"],         "H": ["m11", "m00"]},
    "$_XNOR_": {"L": ["m11", "m00"],         "H": ["m10", "m01"]},
}
# port letter for each yosys pin, and the yosys output pin
G2_PINS = {"a": "A", "b": "B"}
# MUX: 8 TH33 minterms over (s,a,b) — from ncl_gates.vhd ncl_mux2
MUX_MIN = {
    "m010": ("th33", [("s", "H"), ("a", "L"), ("b", "H")]),
    "m011": ("th33", [("s", "H"), ("a", "L"), ("b", "L")]),
    "m101": ("th33", [("s", "L"), ("a", "H"), ("b", "L")]),
    "m111": ("th33", [("s", "L"), ("a", "L"), ("b", "L")]),
    "m000": ("th33", [("s", "H"), ("a", "H"), ("b", "H")]),
    "m001": ("th33", [("s", "H"), ("a", "H"), ("b", "L")]),
    "m100": ("th33", [("s", "L"), ("a", "H"), ("b", "H")]),
    "m110": ("th33", [("s", "L"), ("a", "L"), ("b", "H")]),
}
MUX_RAILS = {"L": ["m010", "m011", "m101", "m111"], "H": ["m000", "m001", "m100", "m110"]}
COLLECT = {2: "th12", 3: "th13", 4: "th14"}   # threshold-1 rail collector by fan-in


def main():
    argv = sys.argv[1:]
    target = argv[argv.index("--target") + 1] if "--target" in argv else "verilog"
    bind = argv[argv.index("--bind") + 1] if "--bind" in argv else "comb"
    pos = [a for i, a in enumerate(argv)
           if a not in ("--target", "--bind") and (i == 0 or argv[i - 1] not in ("--target", "--bind"))]
    if len(pos) != 3:
        sys.exit(__doc__)
    jpath, top, out = pos
    d = json.load(open(jpath))
    if top not in d["modules"]:
        sys.exit("top '%s' not in %s" % (top, list(d["modules"])))
    m = d["modules"][top]
    ports, cells = m["ports"], m["cells"]

    clock_nets = set()
    for c in cells.values():
        if c["type"].startswith(("$_DFF", "$_SDFF", "$_DFFE", "$_DLATCH")):
            for b in c["connections"].get("C", []):
                if isinstance(b, int):
                    clock_nets.add(b)
    allnets = set()
    for p in ports.values():
        allnets.update(b for b in p["bits"] if isinstance(b, int))
    for c in cells.values():
        if c["type"] == "$scopeinfo":
            continue
        for conn in c["connections"].values():
            allnets.update(b for b in conn if isinstance(b, int))
    dual_nets = sorted(allnets - clock_nets)

    V = (target == "verilog")

    def rail(bit, r):
        """rail r ('L'|'H') of a data bit -> target expression."""
        if isinstance(bit, int):
            return ("n%d_%s" % (bit, r)) if V else ("n%d.%s" % (bit, r))
        # constants: DATA0=(L0,H1), DATA1=(L1,H0)
        one = "1'b1" if V else "'1'"
        zero = "1'b0" if V else "'0'"
        if bit == "0":
            return zero if r == "L" else one
        if bit == "1":
            return one if r == "L" else zero
        sys.exit("unsupported constant bit %r" % bit)

    def clk(bit):
        return ("c%d" % bit) if isinstance(bit, int) else sys.exit("clock must be a net")

    body = []          # instance/assign lines
    minterm_sigs = []  # std_logic minterm nets to declare (vhdl)
    gi = [0]

    def emit_cell(inst_pins, out_bit, minterms, rails):
        """inst_pins: {port_letter: bit}; minterms: {label:(cell,[(port,rail)])};
        rails: {'L':[labels],'H':[labels]} -> drive out_bit's two rails."""
        g = gi[0]; gi[0] += 1
        made = {}
        for lbl, (cell, args) in minterms.items():
            sig = "m%d_%s" % (g, lbl)
            minterm_sigs.append(sig)
            ins = [rail(inst_pins[port], r) for port, r in args]
            made[lbl] = sig
            body.append(th_inst(cell, ins, sig))
        for r in ("L", "H"):
            labels = rails[r]
            outr = rail(out_bit, r)
            if len(labels) == 1:
                body.append(assign(outr, made[labels[0]]))
            else:
                body.append(th_inst(COLLECT[len(labels)], [made[l] for l in labels], outr))

    def th_inst(cell, ins, y):
        pnames = ["a", "b", "c", "d"][:len(ins)]
        if V:
            args = ", ".join(".%s(%s)" % (p, s) for p, s in zip(pnames, ins)) + ", .y(%s)" % y
            return "  %s u%d (%s);" % (cell, uid(), args)
        args = ", ".join("%s => %s" % (p, s) for p, s in zip(pnames, ins)) + ", y => %s" % y
        return "  u%d: entity work.%s(%s) port map (%s);" % (uid(), cell, bind, args)

    _uid = [0]
    def uid():
        _uid[0] += 1
        return _uid[0]

    def assign(lhs, rhs):
        return ("  assign %s = %s;" % (lhs, rhs)) if V else ("  %s <= %s;" % (lhs, rhs))

    # ---- port wiring ----
    for pname, p in ports.items():
        w = len(p["bits"])
        is_clk = (w == 1 and p["direction"] == "input" and p["bits"][0] in clock_nets)
        for i, b in enumerate(p["bits"]):
            if is_clk:
                body.append(assign(clk(b), pname))
                continue
            body.append(port_wire(V, pname, i, w, b, p["direction"]))

    # ---- cells ----
    unhandled = []
    for cname, c in cells.items():
        t = c["type"]; conn = c["connections"]
        if t == "$scopeinfo":
            continue
        if t == "$_BUF_":
            for r in ("L", "H"):
                body.append(assign(rail(conn["Y"][0], r), rail(conn["A"][0], r)))
            continue
        if t == "$_NOT_":                    # dual-rail inverter = rail swap (free)
            body.append(assign(rail(conn["Y"][0], "L"), rail(conn["A"][0], "H")))
            body.append(assign(rail(conn["Y"][0], "H"), rail(conn["A"][0], "L")))
            continue
        if t in G2_RAILS:
            emit_cell({"a": conn["A"][0], "b": conn["B"][0]}, conn["Y"][0], MIN4, G2_RAILS[t])
            continue
        if t == "$_MUX_":
            emit_cell({"s": conn["S"][0], "a": conn["A"][0], "b": conn["B"][0]}, conn["Y"][0], MUX_MIN, MUX_RAILS)
            continue
        if t == "$_DFF_P_":
            body.append(dff_inst(V, clk(conn["C"][0]), conn["D"][0], conn["Q"][0], rail))
            continue
        unhandled.append(t)
    if unhandled:
        sys.exit("unhandled cell types: %s (fold with dfflegalize/simplemap first)" % sorted(set(unhandled)))

    text = (emit_verilog if V else emit_vhdl)(top, ports, dual_nets, clock_nets, minterm_sigs, body, clk)
    open(out, "w").write(text)
    ng = sum(1 for c in cells.values() if c["type"] in G2_RAILS or c["type"] == "$_MUX_")
    print("wrote %s (target=%s%s): %d gate cells -> TH-cell instances, %d data nets, %d minterm nets"
          % (out, target, "" if V else "/bind=" + bind, ng, len(dual_nets), len(minterm_sigs)))


def port_wire(V, pname, i, w, bit, direction):
    if not isinstance(bit, int):
        return "  // const port bit" if V else "  -- const port bit"
    if V:
        pl = "%s_L[%d]" % (pname, i) if w > 1 else "%s_L" % pname
        ph = "%s_H[%d]" % (pname, i) if w > 1 else "%s_H" % pname
        if direction == "input":
            return "  assign n%d_L = %s; assign n%d_H = %s;" % (bit, pl, bit, ph)
        return "  assign %s = n%d_L; assign %s = n%d_H;" % (pl, bit, ph, bit)
    acc = pname if w == 1 else "%s(%d)" % (pname, i)
    if direction == "input":
        return "  n%d <= %s;" % (bit, acc)
    return "  %s <= n%d;" % (acc, bit)


def dff_inst(V, c, dbit, qbit, rail):
    if V:
        return ("  ncl_dff r (.clk(%s), .d_L(%s), .d_H(%s), .q_L(%s), .q_H(%s));"
                % (c, rail(dbit, "L"), rail(dbit, "H"), rail(qbit, "L"), rail(qbit, "H")))
    return "  r: entity work.ncl_dff port map (clk => %s, d => n%d, q => n%d);" % (c, dbit, qbit)


TH_PORTS = {"th12": 2, "th13": 3, "th14": 4, "th22": 2, "th23": 3, "th33": 3,
            "th24": 4, "th34": 4, "th44": 4, "th23w2": 3, "th34w2": 4}


def emit_verilog(top, ports, dual_nets, clock_nets, minterm_sigs, body, clk):
    L = ["// GENERATED by nulex map_ncl_struct.py --target verilog -- do not edit.",
         "// Structural dual-rail NCL threshold-gate netlist; TH cells are blackboxes",
         "// so they survive `yosys flatten` for constraints.py fork extraction."]
    for cell, n in TH_PORTS.items():
        pins = ", ".join("input %s" % p for p in ["a", "b", "c", "d"][:n])
        L.append("(* blackbox *) module %s(%s, output y); endmodule" % (cell, pins))
    L.append("(* blackbox *) module ncl_dff(input clk, input d_L, input d_H, output q_L, output q_H); endmodule")
    # module + ports
    pl = []
    for pname, p in ports.items():
        w = len(p["bits"]); d = "input" if p["direction"] == "input" else "output"
        is_clk = (w == 1 and p["direction"] == "input" and p["bits"][0] in clock_nets)
        if is_clk:
            pl.append("%s %s" % (d, pname)); continue
        rng = "" if w == 1 else "[%d:0] " % (w - 1)
        pl.append("%s %s%s_L" % (d, rng, pname)); pl.append("%s %s%s_H" % (d, rng, pname))
    L.append("module %s (%s);" % (top, ", ".join(pl)))
    for b in dual_nets:
        L.append("  wire n%d_L, n%d_H;" % (b, b))
    for c in sorted(clock_nets):
        L.append("  wire c%d;" % c)
    for s in minterm_sigs:
        L.append("  wire %s;" % s)
    L += body
    L.append("endmodule")
    return "\n".join(L) + "\n"


def emit_vhdl(top, ports, dual_nets, clock_nets, minterm_sigs, body, clk):
    L = ["-- GENERATED by nulex map_ncl_struct.py --target vhdl -- do not edit.",
         "-- Structural dual-rail NCL threshold-gate netlist (th_cells.vhd instances).",
         "library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;",
         "", "entity %s is" % top]
    pl = []
    for pname, p in ports.items():
        w = len(p["bits"]); dir_ = "in" if p["direction"] == "input" else "out"
        is_clk = (w == 1 and p["direction"] == "input" and p["bits"][0] in clock_nets)
        if is_clk:
            pl.append("    %s : in std_logic" % pname); continue
        ty = "ncl_logic" if w == 1 else "ncl_logic_vector(%d downto 0)" % (w - 1)
        pl.append("    %s : %s %s" % (pname, dir_, ty))
    L.append("  port (\n" + ";\n".join(pl) + "\n  );")
    L.append("end entity %s;" % top)
    L.append("architecture th_struct of %s is" % top)
    ids = dual_nets
    for i in range(0, len(ids), 16):
        L.append("  signal " + ", ".join("n%d" % b for b in ids[i:i + 16]) + " : ncl_logic;")
    if clock_nets:
        L.append("  signal " + ", ".join("c%d" % b for b in sorted(clock_nets)) + " : std_logic;")
    for i in range(0, len(minterm_sigs), 16):
        L.append("  signal " + ", ".join(minterm_sigs[i:i + 16]) + " : std_logic;")
    L.append("begin")
    L += body
    L.append("end architecture th_struct;")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
