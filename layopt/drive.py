# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Two-edge driver model, calibrated from a Liberty file.

A CMOS stage drives its net through the PMOS on the rising edge and the
NMOS on the falling edge, so a delay model that only knows one resistance
prices NMOS sizing at zero.  This module reads the characterized cells'
rise/fall delay tables (delay vs input slew and output load), takes the
slope of delay against load at a chosen slew -- that slope divided by ln 2
is the Elmore-equivalent driver resistance of that edge -- and the intercept
as the stage's intrinsic (self-load) delay.  Against the transistor widths
layopt extracts from the same cells' GDS this gives one constant per edge,
k_p = R_rise * W_p and k_n = R_fall * W_n, which is the model a move then
uses: a device of width W drives with k / W on its edge, series stacks add.

Units: Liberty ns and pF are converted to ps, fF and ohms.  Only the parts
of Liberty needed here are parsed (cell, pin, timing, the delay tables, pin
capacitance); the parser is a bracket walker, not a grammar.
"""
import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

LN2 = math.log(2.0)


@dataclass
class Arc:
    related_pin: str
    sense: str                                  # positive_unate / negative_unate / non_unate
    slews: List[float]                          # ps
    loads: List[float]                          # fF
    rise: List[List[float]]                     # ps, [slew][load]
    fall: List[List[float]]
    rise_tr: Optional[List[List[float]]] = None  # output transition tables, same axes
    fall_tr: Optional[List[List[float]]] = None


@dataclass
class Pin:
    name: str
    direction: str = ""
    capacitance_fF: float = 0.0
    arcs: List[Arc] = field(default_factory=list)


@dataclass
class Cell:
    name: str
    area: float = 0.0
    pins: Dict[str, Pin] = field(default_factory=dict)

    def output(self) -> Optional[Pin]:
        outs = [p for p in self.pins.values() if p.direction == "output" and p.arcs]
        return outs[0] if outs else None


_NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _numbers(s: str) -> List[float]:
    return [float(x) for x in _NUM.findall(s)]


def read_liberty(path: str, cells: Optional[Sequence[str]] = None) -> Dict[str, Cell]:
    """Parse the cells (all, or those named) into Cell records.  Streams the
    file once; the sky130_fd_sc_hd tt library (12.8 MB) takes a few seconds."""
    want = set(cells) if cells else None
    out: Dict[str, Cell] = {}
    cell: Optional[Cell] = None
    pin: Optional[Pin] = None
    arc: Optional[dict] = None
    table: Optional[Tuple[str, dict]] = None     # (kind, dict) being filled: index_1/index_2/values
    depth = 0
    cell_depth = pin_depth = arc_depth = table_depth = -1
    buf = ""
    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("/*") or line.startswith("*"):
                continue
            m = re.match(r'cell\s*\(\s*"?([^")]+)"?\s*\)\s*\{', line)
            if m and depth == 1:
                name = m.group(1)
                cell = Cell(name) if (want is None or name in want) else None
                cell_depth = depth
            elif cell is not None:
                m = re.match(r'pin\s*\(\s*"?([^")]+)"?\s*\)\s*\{', line)
                if m and depth == cell_depth + 1:
                    pin = Pin(m.group(1)); pin_depth = depth
                elif pin is not None and depth == pin_depth + 1 and line.startswith("direction"):
                    pin.direction = line.split(":")[1].strip(" ;\"")
                elif pin is not None and depth == pin_depth + 1 and line.startswith("capacitance"):
                    pin.capacitance_fF = _numbers(line.split(":")[1])[0] * 1000.0
                elif pin is not None and re.match(r'timing\s*\(\s*\)\s*\{', line) and depth == pin_depth + 1:
                    arc = {"related_pin": "", "sense": "", "tables": {}}; arc_depth = depth
                elif arc is not None and depth == arc_depth + 1:
                    if line.startswith("related_pin"):
                        arc["related_pin"] = line.split(":")[1].strip(" ;\"")
                    elif line.startswith("timing_sense"):
                        arc["sense"] = line.split(":")[1].strip(" ;\"")
                    else:
                        m = re.match(r'(cell_rise|cell_fall|rise_transition|fall_transition)\s*\(', line)
                        if m:
                            arc["tables"][m.group(1)] = {}; table = (m.group(1), arc["tables"][m.group(1)]); table_depth = depth
                elif table is not None and depth == table_depth + 1:
                    m = re.match(r'(index_1|index_2|values)\s*\((.*)$', line, re.S)
                    if m:
                        body = m.group(2)
                        buf = body
                        # values may continue over several lines ending with "\"
                        while buf.rstrip().endswith("\\"):
                            nxt = next(fh).strip()
                            buf = buf.rstrip("\\") + " " + nxt
                        table[1][m.group(1)] = _numbers(buf)
                elif line.startswith("area") and depth == cell_depth + 1:
                    cell.area = _numbers(line.split(":")[1])[0]
            # bracket depth bookkeeping (after handling the line's own openers)
            depth += line.count("{") - line.count("}")
            if cell is not None:
                if table is not None and depth <= table_depth:
                    table = None; table_depth = -1
                if arc is not None and depth <= arc_depth:
                    t = arc["tables"]
                    if "cell_rise" in t and "cell_fall" in t and pin is not None:
                        r, f = t["cell_rise"], t["cell_fall"]
                        slews = [v * 1000.0 for v in r["index_1"]]; loads = [v * 1000.0 for v in r["index_2"]]
                        nl = len(loads)
                        grid = lambda tab: [[v * 1000.0 for v in tab["values"][i * nl:(i + 1) * nl]] for i in range(len(slews))]
                        rise, fall = grid(r), grid(f)
                        rtr = grid(t["rise_transition"]) if "rise_transition" in t and "values" in t["rise_transition"] else None
                        ftr = grid(t["fall_transition"]) if "fall_transition" in t and "values" in t["fall_transition"] else None
                        pin.arcs.append(Arc(arc["related_pin"], arc["sense"], slews, loads, rise, fall, rtr, ftr))
                    arc = None; arc_depth = -1
                if pin is not None and depth <= pin_depth:
                    cell.pins[pin.name] = pin; pin = None; pin_depth = -1
                if depth <= cell_depth:
                    out[cell.name] = cell; cell = None; cell_depth = -1
            elif depth <= cell_depth and cell_depth >= 0:
                cell_depth = -1
    return out


@dataclass
class EdgeFit:
    r_ohm: float            # Elmore-equivalent driver resistance: d(delay)/d(load) / ln2
    t0_ps: float            # intrinsic delay at zero load (intercept)
    slew_ps: float
    points: int


def edge_fit(arc: Arc, edge: str, slew_ps: Optional[float] = None, min_load_fF: float = 0.0) -> EdgeFit:
    """Linear fit of delay vs load on one edge at the table slew nearest
    `slew_ps` (default: the smallest), over loads >= min_load_fF (the whole
    row by default; delay vs load is close to linear for these tables)."""
    si = 0 if slew_ps is None else min(range(len(arc.slews)), key=lambda i: abs(arc.slews[i] - slew_ps))
    ys = arc.rise[si] if edge == "rise" else arc.fall[si]
    pts = [(c, y) for c, y in zip(arc.loads, ys) if c >= min_load_fF]
    n = len(pts)
    sx = sum(c for c, _ in pts); sy = sum(y for _, y in pts)
    sxx = sum(c * c for c, _ in pts); sxy = sum(c * y for c, y in pts)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)             # ps/fF = kohm
    t0 = (sy - slope * sx) / n
    return EdgeFit(slope * 1000.0 / LN2, t0, arc.slews[si], n)


@dataclass
class SlewFit:
    """Slew behaviour of one edge of one arc, R fixed from the load slope
    (delays are 50 % delays; R*C is the Elmore moment, ln2*R*C its 50 % point):

        delay(s, C)  = t0 + ln2*R*C + kappa * (R*C) * s / (R*C + mu * s)
        trans(s, C)  = sqrt((tau0 + lam*R*C)^2 + (nu * s)^2)

    kappa is the slew sensitivity when the stage is slower than its input
    (R*C >> s), mu sets how it fades when the stage is faster; nu is the
    slew-limited part of the output transition, lam ~ 1 its RC part."""
    t0_ps: float
    kappa: float
    mu: float
    lam: float
    tau0_ps: float
    nu: float
    rms_ps: float           # delay fit residual over the fitted region


def slew_fit(arc: Arc, edge: str, r_ohm: float, slew_max_ps: float = 700.0) -> SlewFit:
    ys = arc.rise if edge == "rise" else arc.fall
    tr = arc.rise_tr if edge == "rise" else arc.fall_tr
    si = [i for i, sw in enumerate(arc.slews) if sw <= slew_max_ps] or [0]
    pts = [(arc.slews[i], arc.loads[j] * r_ohm / 1000.0, ys[i][j]) for i in si for j in range(len(arc.loads))]   # (s, RC, delay)
    best = None
    for k in range(60):                                  # mu on a log grid 0.003 .. 3
        mu = 0.003 * (1000.0 ** (k / 59.0))
        # linear LS for t0, kappa: delay - RC = t0 + kappa * g,  g = RC*s/(RC + mu*s)
        gs = [(rc * s_) / (rc + mu * s_) for s_, rc, _ in pts]
        zs = [d - LN2 * rc for s_, rc, d in pts]
        n = len(pts); mg = sum(gs) / n; mz = sum(zs) / n
        sgg = sum((g - mg) ** 2 for g in gs)
        kappa = sum((g - mg) * (z - mz) for g, z in zip(gs, zs)) / sgg if sgg else 0.0
        t0 = mz - kappa * mg
        rms = (sum((z - t0 - kappa * g) ** 2 for g, z in zip(gs, zs)) / n) ** 0.5
        if best is None or rms < best[0]:
            best = (rms, mu, kappa, t0)
    rms, mu, kappa, t0 = best
    lam = tau0 = nu = 0.0
    if tr is not None:
        row = tr[0]
        n = len(row); mx = sum(arc.loads) / n; my = sum(row) / n
        sxx = sum((x - mx) ** 2 for x in arc.loads)
        sl = sum((x - mx) * (y - my) for x, y in zip(arc.loads, row)) / sxx
        lam = sl * 1000.0 / r_ohm if r_ohm else 0.0
        tau0 = my - sl * mx
        # nu: trans^2 = base^2 + (nu s)^2 over slews <= 300 ps (the regime a sized path sees)
        num = den = 0.0
        for i, s_ in enumerate(arc.slews):
            if s_ > 300.0:
                continue
            for j in range(len(arc.loads)):
                base = tau0 + lam * r_ohm * arc.loads[j] / 1000.0
                num += max(tr[i][j] ** 2 - base ** 2, 0.0) * s_ ** 2; den += s_ ** 4
        nu = (num / den) ** 0.5 if den else 0.0
    return SlewFit(t0, kappa, mu, lam, tau0, nu, rms)


@dataclass
class DriveModel:
    """Elmore-equivalent driver resistance per edge from the device widths:

        R_rise(W_p) = k_p * W_p^(-beta_p)        (ohm; W in um; k at W = 1 um)
        R_fall(W_n) = k_n * W_n^(-beta_n)

    beta = 1 would be the ideal 1/W; sky130's Liberty says the PMOS falls
    short of it (beta_p ~ 0.84: a 16x wider inverter has ~65% more R*W) while
    the NMOS nearly keeps it (beta_n ~ 0.93).  A series stack of n devices
    costs 1 + (n - 1) * (stack - 1) single devices of that polarity, fitted
    from the nand2/nor2 arcs against same-size inverters (2.3 for PMOS, 1.6
    for NMOS, not the naive 2).  t0 is the intrinsic (zero-load) delay per
    edge of the reference inverter (inv_1)."""
    k_p: float
    k_n: float
    beta_p: float = 1.0
    beta_n: float = 1.0
    stack_p: float = 2.0
    stack_n: float = 2.0
    t0_rise_ps: float = 0.0
    t0_fall_ps: float = 0.0
    # slew (see SlewFit): delay adds kappa*RC*s/(RC + mu*s); output transition is
    # sqrt((tau0 + lam*RC)^2 + (nu*s)^2)
    kappa_rise: float = 0.0
    kappa_fall: float = 0.0
    mu_rise: float = 1.0
    mu_fall: float = 1.0
    lam_rise: float = 1.0
    lam_fall: float = 1.0
    tau0_rise_ps: float = 0.0
    tau0_fall_ps: float = 0.0
    nu_rise: float = 0.0
    nu_fall: float = 0.0

    def stage(self, edge: str, w_um: float, c_total_fF: float, elmore_ps: float, slew_in_ps: float,
              stack: int = 1, flavour: Optional[str] = None) -> Tuple[float, float]:
        """(50 % delay, output transition) in ps for one edge of a stage: R from
        the width, the Elmore moment to the receiver as given (its 50 % point is
        ln2 times it), the stage's own time constant R*C_total for the slew terms."""
        r = self.r_rise(w_um, stack, flavour) if edge == "rise" else self.r_fall(w_um, stack, flavour)
        rc = r * c_total_fF / 1000.0
        if edge == "rise":
            t0, kappa, mu, lam, tau0, nu = self.t0_rise_ps, self.kappa_rise, self.mu_rise, self.lam_rise, self.tau0_rise_ps, self.nu_rise
        else:
            t0, kappa, mu, lam, tau0, nu = self.t0_fall_ps, self.kappa_fall, self.mu_fall, self.lam_fall, self.tau0_fall_ps, self.nu_fall
        delay = t0 + LN2 * elmore_ps + (kappa * rc * slew_in_ps / (rc + mu * slew_in_ps) if rc + mu * slew_in_ps > 0 else 0.0)
        trans = ((tau0 + lam * rc) ** 2 + (nu * slew_in_ps) ** 2) ** 0.5
        return delay, trans

    # Vt flavour multipliers on R (measured in Xyce against the standard device:
    # probes/layopt/vt_fit.py); set from Tech.vt by the tech record
    # keyed by (polarity, flavour), relative to the library's default flavour of that
    # polarity (the one the k's were fitted on); set from Tech.vt / Tech.default_vt
    vt_mult: Dict[Tuple[str, str], float] = field(default_factory=dict)

    def r_rise(self, w_p_um: float, stack: int = 1, flavour: Optional[str] = None) -> float:
        m = self.vt_mult.get(("p", flavour), 1.0) if flavour else 1.0
        return self.k_p * max(w_p_um, 1e-9) ** (-self.beta_p) * (1.0 + (stack - 1) * (self.stack_p - 1.0)) * m

    def r_fall(self, w_n_um: float, stack: int = 1, flavour: Optional[str] = None) -> float:
        m = self.vt_mult.get(("n", flavour), 1.0) if flavour else 1.0
        return self.k_n * max(w_n_um, 1e-9) ** (-self.beta_n) * (1.0 + (stack - 1) * (self.stack_n - 1.0)) * m


def loglog_fit(pairs: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    """R = k * W^(-beta) by least squares in log space over (W, R) pairs.
    Returns (k at W = 1, beta)."""
    xs = [math.log(w) for w, _ in pairs]; ys = [math.log(r) for _, r in pairs]
    n = len(pairs); mx = sum(xs) / n; my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx > 0 else 0.0
    return math.exp(my - slope * mx), -slope
