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
  --target spice    PHYS BINDING: a transistor-level SG13G2 .subckt instantiating
                    the real TH-cell subckts (ldx/asic/cells/th22.sp + th_gates.sp
                    + lib/th_cells_sg13g2.sp) with PSP103 devices — the async block
                    lowered to silicon for LVS / extraction / SPICE in the SG13G2
                    domain. Dual-rail nets are node pairs n{bit}_L/_H; collectors,
                    the NOT rail-swap, and port wiring are resolved by NODE ALIASING
                    (union-find over the ties -> canonical nodes; no 0-ohm resistors).
                    Combinational only so far (sequential cells rejected; use vhdl).

Rail convention (lib/ncl): .L = value-1 (t), .H = value-0 (f). DATA0=(L0,H1),
DATA1=(L1,H0), NULL=(0,0). A dual-rail net n{bit} is two std_logic rails.

Usage: map_ncl_struct.py <netlist.json> <top> <out> [--target vhdl|verilog|spice] [--bind comb|qdi]
"""
import json
import re
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
    reg_mode = argv[argv.index("--reg") + 1] if "--reg" in argv else "sync"   # sync | qdi (pipeline) | desync (feedback)
    if reg_mode == "desync":
        bind = "comb"   # desync needs a stateless (RTZ-capable) datapath; the register times it
    flags = ("--target", "--bind", "--reg")
    pos = [a for i, a in enumerate(argv)
           if a not in flags and (i == 0 or argv[i - 1] not in flags)]
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
    S = (target == "spice")   # phys binding: transistor-level SG13G2 netlist

    def rail(bit, r):
        """rail r ('L'|'H') of a data bit -> target expression."""
        if isinstance(bit, int):
            if S:
                return "n%d_%s" % (bit, r)
            return ("n%d_%s" % (bit, r)) if V else ("n%d.%s" % (bit, r))
        # constants: DATA0=(L0,H1), DATA1=(L1,H0)
        if S:
            one, zero = "VDD", "VSS"   # rail node tied to the supply rails
        else:
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
        if S:
            # SPICE subckt call: X<uid> <inputs...> <y> VDD VSS <cell>
            # (th cell subckt port order is A B [C D] Y VDD VSS)
            return "  X%d %s %s VDD VSS %s" % (uid(), " ".join(ins), y, cell)
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
        if S:
            # SPICE net alias: 0-ohm tie (rhs is a driven cell output / port node).
            return "  R%d %s %s 0" % (uid(), lhs, rhs)
        return ("  assign %s = %s;" % (lhs, rhs)) if V else ("  %s <= %s;" % (lhs, rhs))

    # ---- port wiring ----
    for pname, p in ports.items():
        w = len(p["bits"])
        is_clk = (w == 1 and p["direction"] == "input" and p["bits"][0] in clock_nets)
        for i, b in enumerate(p["bits"]):
            if is_clk:
                if S:
                    sys.exit("--target spice: clocked/sequential designs not supported yet "
                             "(combinational phys binding only)")
                body.append(assign(clk(b), pname))
                continue
            body.append(port_wire(V, pname, i, w, b, p["direction"], S))

    # ---- cells ----
    reg_bits = []          # (dbit, qbit) for --reg qdi (a single-stage QDI bank)
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
            if S:
                sys.exit("--target spice: sequential cells ($_DFF_P_) not supported yet "
                         "(combinational phys binding only; use --target vhdl for registers)")
            if reg_mode in ("qdi", "desync"):
                reg_bits.append((cname, conn["D"][0], conn["Q"][0]))   # bound below per reg_mode
            else:
                body.append(dff_inst(V, clk(conn["C"][0]), conn["D"][0], conn["Q"][0], rail))
            continue
        unhandled.append(t)
    if unhandled:
        sys.exit("unhandled cell types: %s (fold with dfflegalize/simplemap first)" % sorted(set(unhandled)))

    # ---- QDI pipeline (--reg qdi): assign registers to 4-phase STAGES by their
    #      register-to-register dependency depth, build a QDI register per stage,
    #      and wire the handshake: stage s request ki_s = NOT(ko of stage s+1);
    #      completion ko_s = C-element chain over the stage's per-bit is-DATA.
    #      ki of the last (output) stage is the external ki_in; ko_out/ko_in expose
    #      the output/input completions. TH cells only -> the per-stage request
    #      distribution and completion-tree forks are all extractable. ----
    extra_ports = []
    reg_decls = []
    if reg_bits and reg_mode == "desync":
        # Feedback/cyclic: one desync register bank (ncl_reg_desync) captured by a
        # matched-delay completion clock. Handles register cycles the QDI pipeline
        # rejects; the datapath is comb (RTZ). VHDL target (a clocked register).
        if V:
            sys.exit("--reg desync targets --target vhdl (a local-clock register process)")
        K = len(reg_bits)
        extra_ports = [("done", "output", "std_logic")]      # local self-timed clock, for pacing
        reg_decls.append("  signal dreg, qreg : ncl_logic_vector(%d downto 0);" % (K - 1))
        for i, (cname, dbit, qbit) in enumerate(reg_bits):
            body.append("  dreg(%d) <= n%d;" % (i, dbit))     # next-state bit -> bank input
            body.append("  n%d <= qreg(%d);" % (qbit, i))     # bank output -> state net (feedback)
        body.append("  reg_desync: entity work.ncl_reg_desync generic map (N => %d) "
                    "port map (d => dreg, q => qreg, done => done);" % K)
    elif reg_bits:                                            # reg_mode == "qdi": multi-stage pipeline
        stage_of = pipeline_stages(cells)                     # reg cell name -> stage
        maxs = max(stage_of[c] for c, _, _ in reg_bits)
        by_stage = {}
        for cname, dbit, qbit in reg_bits:
            by_stage.setdefault(stage_of[cname], []).append((dbit, qbit))
        extra_ports = [("ki_in", "input", "std_logic"),
                       ("ko_out", "output", "std_logic"), ("ko_in", "output", "std_logic")]
        NOT = (lambda a: "~" + a) if V else (lambda a: "not " + a)
        for s in range(maxs + 1):
            kis = "ki_in" if s == maxs else "ki_s%d" % s        # request into stage s
            kos = "ko_s%d" % s
            if s != maxs:
                minterm_sigs.append(kis)
                body.append(assign(kis, NOT("ko_s%d" % (s + 1))))   # ki_s = NOT(downstream ko)
            minterm_sigs.append(kos)
            cds = []
            for j, (dbit, qbit) in enumerate(by_stage[s]):
                body.append(th_inst("th22", [rail(dbit, "L"), kis], rail(qbit, "L")))
                body.append(th_inst("th22", [rail(dbit, "H"), kis], rail(qbit, "H")))
                cd = "cd_s%d_%d" % (s, j); minterm_sigs.append(cd); cds.append(cd)
                body.append(th_inst("th12", [rail(qbit, "L"), rail(qbit, "H")], cd))
            # C-element completion tree.  This used to be a LINEAR chain
            # (acc(j) = TH22(acc(j-1), cd(j))), which costs the same N-1 TH22
            # cells but has depth N-1 instead of ceil(log2 N): at W=24 that is
            # ~24 TH22 delays of completion for a datapath only 9 deep, i.e. the
            # detector, not the logic, sets the cycle time.  A balanced tree is
            # the same cell count and the same function (C-elements associate).
            lvl, k = list(cds), 0
            while len(lvl) > 1:
                nxt = []
                for j in range(0, len(lvl), 2):
                    if j + 1 < len(lvl):
                        acc = "acc_s%d_%d_%d" % (s, k, j // 2)
                        minterm_sigs.append(acc)
                        body.append(th_inst("th22", [lvl[j], lvl[j + 1]], acc))
                        nxt.append(acc)
                    else:
                        nxt.append(lvl[j])
                lvl, k = nxt, k + 1
            body.append(assign(kos, lvl[0]))
        body.append(assign("ko_out", "ko_s%d" % maxs))
        body.append(assign("ko_in", "ko_s0"))

    if V:
        text = emit_verilog(top, ports, dual_nets, clock_nets, minterm_sigs, body, extra_ports)
    elif S:
        text = emit_spice(top, ports, dual_nets, clock_nets, minterm_sigs, body, extra_ports)
    else:
        text = emit_vhdl(top, ports, dual_nets, clock_nets, minterm_sigs, body, extra_ports, reg_decls)
    open(out, "w").write(text)
    ng = sum(1 for c in cells.values() if c["type"] in G2_RAILS or c["type"] == "$_MUX_")
    print("wrote %s (target=%s%s): %d gate cells -> TH-cell instances, %d data nets, %d minterm nets"
          % (out, target, "" if V else "/bind=" + bind, ng, len(dual_nets), len(minterm_sigs)))


def pipeline_stages(cells):
    """Assign each $_DFF_P_ register a 4-phase pipeline STAGE = its depth in the
    register-to-register dependency graph (0 = captures from primary inputs).
    A register R depends on R' if R''s Q is in R's D backward comb cone. Raises on
    register feedback (a cyclic dependency is not a feed-forward pipeline)."""
    drv = {}                       # net -> driving comb cell
    reg_of_q, reg_d = {}, {}       # q_net -> reg name ; reg name -> d_net
    for name, c in cells.items():
        t = c["type"]
        if t == "$_DFF_P_":
            reg_of_q[c["connections"]["Q"][0]] = name
            reg_d[name] = c["connections"]["D"][0]
        elif t != "$scopeinfo":
            for b in c["connections"].get("Y", []):
                if isinstance(b, int):
                    drv[b] = c

    def deps_of(dnet):
        seen, stack, regs = set(), [dnet], set()
        while stack:
            n = stack.pop()
            if not isinstance(n, int):
                continue
            if n in reg_of_q:
                regs.add(reg_of_q[n]); continue      # boundary: another register's Q
            if n in seen:
                continue
            seen.add(n)
            c = drv.get(n)
            if c is None:
                continue                              # primary input / constant
            for pin, conns in c["connections"].items():
                if pin == "Y":
                    continue
                stack.extend(conns)
        return regs

    deps = {r: deps_of(reg_d[r]) for r in reg_d}
    stage = {}

    def st(r, path):
        if r in stage:
            return stage[r]
        if r in path:
            raise SystemExit("register feedback loop through %s: not a feed-forward pipeline "
                             "(async desync of cyclic logic is out of scope)" % r)
        s = 0 if not deps[r] else 1 + max(st(x, path | {r}) for x in deps[r])
        stage[r] = s
        return s

    for r in reg_d:
        st(r, set())
    return stage


def spice_port_nodes(pname, w):
    """The two rail nodes exposed on the .subckt interface for each bit of a port."""
    if w == 1:
        return [("%s_L" % pname, "%s_H" % pname)]
    return [("%s_L_%d" % (pname, i), "%s_H_%d" % (pname, i)) for i in range(w)]


def port_wire(V, pname, i, w, bit, direction, S=False):
    if not isinstance(bit, int):
        return "  * const port bit" if S else ("  // const port bit" if V else "  -- const port bit")
    if S:
        nl, nh = spice_port_nodes(pname, w)[i]
        # 0-ohm ties: input port node -> internal rail net (and out net -> port node).
        return ("  Rpl_%s_%d %s n%d_L 0\n  Rph_%s_%d %s n%d_H 0"
                % (pname, i, nl, bit, pname, i, nh, bit))
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


def emit_spice(top, ports, dual_nets, clock_nets, minterm_sigs, body, extra_ports):
    """Phys binding: a transistor-level SG13G2 .subckt of the dual-rail NCL netlist.
    Each TH cell is a real transistor subckt (th22.sp / th_gates.sp / th_cells_sg13g2.sp),
    so the whole async block is lowerable to silicon (LVS / extraction / SPICE) in the
    SG13G2 domain. Dual-rail nets are node pairs n<bit>_L / n<bit>_H. Rail encoding:
    DATA1=(L=1,H=0), DATA0=(L=0,H=1), NULL=(L=0,H=0).

    Net aliases (a rail collector `y = m`, the NOT rail-swap, and port<->internal-net
    wiring) are resolved by NODE ALIASING, not 0-ohm resistors: the assign()/port_wire()
    passes emit `R... a b 0` ties, and here a union-find collapses each tie into a single
    canonical node (a subckt-port node wins, else VDD/VSS, else the net) which every TH-cell
    instance is rewritten to use. 0-ohm resistors are NOT emitted -- in a multi-cell .subckt
    Xyce mis-reduces chains/fan-outs of them (outputs read stuck-at-0); direct aliasing is
    both correct and cleaner (fewer nodes)."""
    L = ["* GENERATED by nulex map_ncl_struct.py --target spice -- do not edit.",
         "* Transistor-level SG13G2 realization of the dual-rail NCL netlist (phys binding).",
         "* The enclosing deck must provide, before the top subckt is instantiated:",
         "*   .hdl \"<verilog-a>/psp103/psp103.va\"          (PSP103 device)",
         "*   .include \"<sg13g2_psp103_tt.lib>\"             (SG13G2 PSP103 model card)",
         "*   .include \"<ldx>/asic/cells/th22.sp\"           (C-element)",
         "*   .include \"<ldx>/asic/cells/th_gates.sp\"       (th12/th23/th33/th34w2)",
         "*   .include \"<nulex>/lib/th_cells_sg13g2.sp\"     (th13/th14 collectors)",
         "* Each data bit -> two rail nodes <port>_L/_H (or _L_<i>/_H_<i> for a bus).",
         "* Encoding: DATA1=(L=1,H=0)  DATA0=(L=0,H=1)  NULL=(L=0,H=0)."]
    port_set = set()
    pnodes = []
    for pname, p in ports.items():
        w = len(p["bits"])
        if w == 1 and p["direction"] == "input" and p["bits"][0] in clock_nets:
            sys.exit("--target spice: clocked designs not supported yet")
        for nl, nh in spice_port_nodes(pname, w):
            pnodes += [nl, nh]; port_set.update((nl, nh))
    pnodes += [name for name, _, _ in extra_ports]
    port_set.update(name for name, _, _ in extra_ports)

    # --- union-find over the 0-ohm ties; then rewrite instances to canonical nodes ---
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        r = x
        while parent[r] != r:
            r = parent[r]
        while parent[x] != r:
            parent[x], x = r, parent[x]
        return r
    def _pri(n):   # canonical-name preference: port node > supply > ordinary net
        return 2 if n in port_set else (1 if n in ("VDD", "VSS", "0") else 0)
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        parent[(rb if _pri(ra) >= _pri(rb) else ra)] = (ra if _pri(ra) >= _pri(rb) else rb)

    tie = re.compile(r'^\s*R\S+\s+(\S+)\s+(\S+)\s+0\s*$')
    insts = []
    for line in body:
        for sub in line.split("\n"):
            if not sub.strip():
                continue
            m = tie.match(sub)
            if m:
                union(m.group(1), m.group(2))
            else:
                insts.append(sub)
    def canon(t):
        return find(t) if t in parent else t
    # NB: SPICE cards are emitted with NO leading whitespace — Xyce mis-parses
    # indented device cards inside a .subckt (the devices silently fail to bind
    # their supply nodes: "Voltage Node (VDD) connected to only 1 device Terminal",
    # and outputs read stuck-at-0). The vhdl/verilog targets indent freely; SPICE
    # must not.
    L.append(".subckt %s %s VDD VSS" % (top, " ".join(pnodes)))
    for line in insts:
        parts = line.split()
        if parts and parts[0][0] in "Xx":     # X<uid> <nodes...> <cell> -- rewrite node args
            L.append("%s %s %s" % (parts[0], " ".join(canon(t) for t in parts[1:-1]), parts[-1]))
        else:
            L.append(line.strip())
    L.append(".ends %s" % top)
    return "\n".join(L) + "\n"


def emit_verilog(top, ports, dual_nets, clock_nets, minterm_sigs, body, extra_ports):
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
    for name, d, _ in extra_ports:
        pl.append("%s %s" % (d, name))
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


def emit_vhdl(top, ports, dual_nets, clock_nets, minterm_sigs, body, extra_ports, reg_decls=()):
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
    for name, d, _ in extra_ports:
        pl.append("    %s : %s std_logic" % (name, "in" if d == "input" else "out"))
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
    L += list(reg_decls)
    L.append("begin")
    L += body
    L.append("end architecture th_struct;")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
