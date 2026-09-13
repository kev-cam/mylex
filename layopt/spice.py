# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Xyce on the extracted layout: a SPICE deck for a chosen set of cells with
the layout's own transistors (one per finger, on the PDK's BSIM4 models in
the narrowest bin that fits) and the nets' distributed parasitic RC (one node
per conducting shape, the resistances of `rc.net_segments`, each shape's
capacitance to ground), at a process/voltage/temperature corner.

    m = Models(tech, corner="ss")                       # tt | ss | ff, converted once, cached
    d = Deck(ex, insts={"u1", "u6"}, models=m, corner=Corner("ss", 1.60, 100.0))
    d.stimulus(net_id, shape_id, edge="rise", slew_ps=50)   # a PWL source on that node
    d.measure("a_rise", trig=(in_shape, 0.5, "rise"), targ=(out_shape, 0.5, "fall"))
    res = d.run(xyce)                                    # {"a_rise": ps, ..., "energy_fJ": ...}

Cells outside the set that a net reaches are loads: their gate shapes on
the net become gate capacitances, the net's wiring is kept whole.  Supply
nets are ideal (every shape one node).
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from . import geom, rc
from .extract import Extraction
from .tech import Tech

PDK = os.path.expanduser("~/tools/sky130_fd_pr")
XYCE = os.path.expanduser("~/tools/xyce/bin/Xyce")
CORNERS = {"tt": (1.80, 25.0), "ss": (1.60, 100.0), "ff": (1.95, -40.0)}     # the library's own corners


@dataclass
class Corner:
    process: str = "tt"
    vdd: float = 1.80
    temp_c: float = 25.0

    @staticmethod
    def named(p: str) -> "Corner":
        v, t = CORNERS[p]
        return Corner(p, v, t)

    @property
    def tag(self) -> str:
        return "%s_%gV_%gC" % (self.process, self.vdd, self.temp_c)


class Models:
    """The PDK model files of one process corner made Xyce-ready (kestrel's recipe:
    the subckt wrapper stripped; every per-cell symbol the file uses but does not
    define set to 0, multipliers to 1; the corner file's offsets not applied) and
    the bin lookup: the narrowest (L, W) bin, since the bins are nested."""

    def __init__(self, tech: Tech, process: str = "tt", pdk: str = PDK, scratch: Optional[str] = None):
        self.tech, self.process, self.pdk = tech, process, pdk
        self.scratch = scratch or os.path.join(pdk, "xyce")
        os.makedirs(self.scratch, exist_ok=True)
        self.files: Dict[str, str] = {}        # model name (sky130_fd_pr__nfet_01v8) -> converted file
        self.params: Dict[str, List[str]] = {}
        self._bins: Dict[str, List[Tuple[str, float, float, float, float]]] = {}

    def file(self, model: str) -> str:
        cell = model.replace("sky130_fd_pr__", "")
        if model not in self.files:
            src = os.path.join(self.pdk, "sky130_fd_pr__%s__%s.pm3.spice" % (cell, self.process))
            dst = os.path.join(self.scratch, "%s_%s.spice" % (cell, self.process))
            if not os.path.exists(dst):
                lines = open(src).read().split("\n"); out = []
                i = 0
                while i < len(lines):
                    ln = lines[i]
                    if ln.startswith(".subckt") or ln.startswith(".ends") or ln.lower().startswith("msky130"):
                        i += 1; continue
                    if ln.startswith("*") and i + 1 < len(lines) and lines[i + 1].startswith("+"):
                        i += 1; continue
                    out.append(ln); i += 1
                open(dst, "w").write("\n".join(out))
            txt = open(dst).read()
            used = set(re.findall(r"(sky130_fd_pr__%s__\w+)" % re.escape(cell), txt))
            defined = set(re.findall(r"^\.param\s+(sky130_fd_pr__\w+)", txt, re.M | re.I))
            self.params[model] = [".PARAM %s = %s" % (n, "1.0" if "mult" in n else "0.0")
                                  for n in sorted(used - defined) if not (n.endswith("__model") or "__model." in n)]
            self.files[model] = dst
        return self.files[model]

    def bin(self, model: str, l_um: float, w_um: float) -> str:
        path = self.file(model)
        if path not in self._bins:
            txt = open(path).read(); res = []
            for m in re.finditer(r"^\.model\s+(\S+)\s+\w+\s*\n((?:\+.*\n)*)", txt, re.M):
                g = {k: float(v) for k, v in re.findall(r"(lmin|lmax|wmin|wmax)\s*=\s*([-+0-9.eE]+)", m.group(2))}
                if len(g) == 4:
                    res.append((m.group(1), g["lmin"], g["lmax"], g["wmin"], g["wmax"]))
            self._bins[path] = res
        l, w = l_um * 1e-6, w_um * 1e-6
        best = None
        for name, lmin, lmax, wmin, wmax in self._bins[path]:
            if lmin <= l < lmax and wmin <= w < wmax:
                key = (wmax - wmin, lmax - lmin)
                if best is None or key < best[0]:
                    best = (key, name)
        if best is None:
            raise KeyError("no %s bin for L=%g W=%g" % (model, l_um, w_um))
        return best[1]


class Deck:
    def __init__(self, ex: Extraction, insts: Set[str], models: Models, corner: Corner = Corner(),
                 gate_cap_fF_um2: Optional[float] = None):
        self.ex, self.insts, self.models, self.corner = ex, set(insts), models, corner
        self.tech = ex.tech
        self.cgate = gate_cap_fF_um2 if gate_cap_fF_um2 is not None else getattr(self.tech, "cgate_fF_um2", 8.63)
        self.sources: List[str] = []
        self.measures: List[str] = []
        self.extra: List[str] = []
        self.tied: Dict[int, str] = {}          # net id -> level a gate-only net is held at
        self.tie_level: Dict[int, str] = {}     # caller's choice per net ("vdd" | "vss")
        self._src_sid: Dict[str, int] = {}
        self._inst_of = lambda prov: prov.split("/")[1] if prov.count("/") >= 2 else prov

    # ---- nodes ----
    def node(self, sid: int) -> str:
        n = self.ex.net_of_shape[sid]
        name = self.ex.nets[n].name
        if name in self.tech.supply_names:
            return "vdd" if name.upper() in ("VDD", "VPWR") or "VD" in name.upper() else "vss"
        return "n%d_%d" % (n, sid)

    def body(self) -> List[str]:
        ex, tech = self.ex, self.tech
        dbu = ex.dbu_um
        lines: List[str] = []
        devs = [dv for dv in ex.devices if self._inst_of(dv.prov) in self.insts]
        nets: Set[int] = set()
        for dv in devs:
            nets.update((dv.g, dv.s, dv.d))
        # S/D shapes per gate finger
        sd_index = geom.BinIndex()
        for sid, sh in enumerate(ex.shapes):
            if sh.layer.startswith("sd_"):
                sd_index.add(sid, sh.rect)
        n_m = 0
        for dv in devs:
            nf = max(1, len(dv.gate_ids))
            model_bin = self.models.bin(dv.model, dv.l, dv.w / nf)
            for k, gsid in enumerate(dv.gate_ids):
                g = ex.shapes[gsid].rect
                if dv.flow_axis == "x":
                    sa, sb = (g[0], g[1], g[0], g[3]), (g[2], g[1], g[2], g[3])
                else:
                    sa, sb = (g[0], g[1], g[2], g[1]), (g[0], g[3], g[2], g[3])
                ta = [s for s in sd_index.query_touch(sa) if ex.shapes[s].layer == "sd_" + dv.kind]
                tb = [s for s in sd_index.query_touch(sb) if ex.shapes[s].layer == "sd_" + dv.kind]
                if not ta or not tb:
                    continue
                s_sid = next((s for s in ta if ex.net_of_shape[s] == dv.s), ta[0])
                d_sid = next((s for s in tb if ex.net_of_shape[s] == dv.d), tb[0])
                if ex.net_of_shape[s_sid] != dv.s:            # the finger is mirrored: swap
                    s_sid, d_sid = d_sid, s_sid
                bulk = "vdd" if dv.kind == "p" else "vss"
                w = dv.w / nf
                n_m += 1
                lines.append("M%d_%s %s %s %s %s %s W=%gu L=%gu AS=%gp AD=%gp PS=%gu PD=%gu" % (
                    n_m, dv.name, self.node(d_sid), self.node(gsid), self.node(s_sid), bulk, model_bin,
                    round(w, 4), round(dv.l, 4), round(dv.as_ / nf, 5), round(dv.ad / nf, 5), round(dv.ps / nf, 4), round(dv.pd / nf, 4)))
        # the nets' wiring: R between shapes, C per shape; foreign gates as capacitors
        n_r = n_c = 0
        for n in sorted(nets):
            net = ex.nets[n]
            if net.name in tech.supply_names:
                continue
            for seg in rc.net_segments(ex, n):
                a, b = self.node(seg.a), self.node(seg.b)
                if a == b:
                    continue
                n_r += 1
                lines.append("R%d %s %s %g" % (n_r, a, b, max(seg.r, 0.1)))     # a floor well under any device: the cut and junction pseudo-segments are near zero
            for sid in net.shapes:
                sh = ex.shapes[sid]
                c = rc.shape_c_fF(ex, sid)
                if sh.layer == "gate" and self._inst_of(sh.prov) not in self.insts:
                    c += self.cgate * (sh.rect[2] - sh.rect[0]) * (sh.rect[3] - sh.rect[1]) * dbu * dbu
                if c > 0:
                    n_c += 1
                    lines.append("C%d %s 0 %gf" % (n_c, self.node(sid), round(c, 5)))
        # an input of the set that nothing drives (a receiver's other input) is held at
        # the level that makes it transparent for the path: VDD for an NMOS-stack input
        # (nand) -- VSS would be right for a nor; the caller may tie explicitly instead
        driven = {self.ex.net_of_shape[sid] for src in self.sources for sid in [self._src_sid[src]]} if hasattr(self, "_src_sid") else set()
        for n in sorted(nets):
            net = self.ex.nets[n]
            if net.name in tech.supply_names or n in driven or n in self.tied:
                continue
            if all(t == "G" for _, t in net.devices) and net.devices:
                lvl = self.tie_level.get(n, "vdd")
                self.tied[n] = lvl
                lines.append("Vtie%d %s %s 0" % (n, self.node(net.shapes[0]), lvl))
        self.stats = {"devices": n_m, "resistors": n_r, "capacitors": n_c, "nets": len(nets), "tied": len(self.tied)}
        return lines

    # ---- stimulus and measures ----
    def stimulus(self, sid: int, edge: str = "rise", t0_ns: float = 1.0, slew_ps: float = 50.0, period_ns: float = 4.0, name: str = "in") -> str:
        v = self.corner.vdd
        lo, hi = (0, v) if edge == "rise" else (v, 0)
        s = slew_ps * 1e-3
        pwl = "PWL(0 %g %gn %g %gn %g %gn %g %gn %g %gn %g)" % (lo, t0_ns, lo, t0_ns + s, hi, t0_ns + period_ns / 2, hi, t0_ns + period_ns / 2 + s, lo, t0_ns + period_ns, lo)
        src = "V%s %s 0 %s" % (name, self.node(sid), pwl)
        self.sources.append(src); self._src_sid[src] = sid
        return self.node(sid)

    def measure(self, name: str, trig: Tuple[int, float, str], targ: Tuple[int, float, str]) -> None:
        v = self.corner.vdd
        (ts, tf, te), (gs, gf, ge) = trig, targ
        self.measures.append(".MEASURE TRAN %s TRIG V(%s)=%g %s=1 TARG V(%s)=%g %s=1" % (
            name, self.node(ts), tf * v, te.upper(), self.node(gs), gf * v, ge.upper()))

    def measure_slew(self, name: str, sid: int, edge: str) -> None:
        v = self.corner.vdd
        lo, hi = (0.2, 0.8) if edge == "rise" else (0.8, 0.2)
        self.measures.append(".MEASURE TRAN %s TRIG V(%s)=%g %s=1 TARG V(%s)=%g %s=1" % (name, self.node(sid), lo * v, edge.upper(), self.node(sid), hi * v, edge.upper()))

    def text(self, t_end_ns: float = 6.0, step_ps: float = 1.0) -> str:
        c = self.corner
        models = sorted({dv.model for dv in self.ex.devices if self._inst_of(dv.prov) in self.insts})
        lines = ["* layopt %s at %s" % (self.ex.top, c.tag)]
        for m in models:
            lines += self.models.params[m] if m in self.models.params else (self.models.file(m) and self.models.params[m])
        lines += ['.INCLUDE "%s"' % self.models.file(m) for m in models]
        lines += [".OPTIONS DEVICE TEMP=%g" % c.temp_c, "VDD vdd 0 %g" % c.vdd, "VSS vss 0 0"]
        lines += self.body() + self.sources + self.extra
        lines += [".TRAN %gp %gn" % (step_ps, t_end_ns), ".OPTIONS TIMEINT RELTOL=1e-4 ABSTOL=1e-12"]
        lines += self.measures + [".MEASURE TRAN q_vdd INTEG I(VDD)", ".END"]
        return "\n".join(lines) + "\n"

    def run(self, path: str, xyce: str = XYCE, t_end_ns: float = 6.0, step_ps: float = 1.0, timeout: int = 1800) -> Dict[str, Optional[float]]:
        open(path, "w").write(self.text(t_end_ns, step_ps))
        p = subprocess.run([xyce, path], capture_output=True, text=True, timeout=timeout, cwd=os.path.dirname(path) or ".")
        out = p.stdout + p.stderr
        mt = open(path + ".mt0").read() if os.path.exists(path + ".mt0") else ""
        res: Dict[str, Optional[float]] = {}
        for m in re.finditer(r"^\s*(\w+)\s*=\s*([-+0-9.eE]+)", mt, re.M):
            res[m.group(1).lower()] = float(m.group(2))
        for m in self.measures:
            k = m.split()[2].lower()
            res.setdefault(k, None)
        if "q_vdd" in res and res["q_vdd"] is not None:
            res["energy_fJ"] = abs(res["q_vdd"]) * self.corner.vdd * 1e15
        res["_ok"] = "DC Operating Point Failed" not in out and bool(mt)
        res["_log"] = out[-800:]
        return res
