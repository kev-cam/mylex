# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# SPDX-FileCopyrightText: 2026 D. Kevin Cameron
"""Optimization loop: variables -> moves on a copy of the layout -> re-extract
-> topology + rule guard -> cost.  Derivative-free (Nelder-Mead, no SciPy),
the same shape as kestrel's sim/opt VCO sizer but with geometry as the
variable and extraction as the evaluator."""
import copy
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from . import drc, extract
from .gds import FlatLayout
from .tech import Tech


@dataclass
class Variable:
    name: str
    lo: float
    hi: float
    x0: float
    apply: Callable[[FlatLayout, "extract.Extraction", float], List[int]]   # returns touched rect ids


@dataclass
class Evaluation:
    x: List[float]
    cost: float
    terms: Dict[str, float]
    legal: bool
    violations: int
    signature_ok: bool
    fl: Optional[FlatLayout] = None
    ex: Optional["extract.Extraction"] = None


class Problem:
    def __init__(self, base: FlatLayout, tech: Tech, variables: Sequence[Variable],
                 cost: Callable[[FlatLayout, "extract.Extraction", Dict[str, float]], Tuple[float, Dict[str, float]]],
                 labels=None, illegal_penalty: float = 1e3, check_rules: bool = True,
                 preserve_topology: bool = True):
        self.base = base
        self.tech = tech
        self.vars = list(variables)
        self.cost_fn = cost
        self.labels = labels
        self.penalty = illegal_penalty
        self.check_rules = check_rules
        self.preserve = preserve_topology
        self.base_ex = extract.extract(base, tech, labels)
        self.base_sig = self.base_ex.signature()
        self.baseline = {drc.key(v) for v in drc.check(base, self.base_ex)} if check_rules else set()
        self.history: List[Evaluation] = []

    def clip(self, x: Sequence[float]) -> List[float]:
        return [min(max(v, var.lo), var.hi) for v, var in zip(x, self.vars)]

    def evaluate(self, x: Sequence[float], keep: bool = False) -> Evaluation:
        x = self.clip(x)
        fl = copy.deepcopy(self.base)
        touched: List[int] = []
        for v, var in zip(x, self.vars):
            touched += var.apply(fl, self.base_ex, v)
        ex = extract.extract(fl, self.tech, self.labels)
        sig_ok = (not self.preserve) or ex.signature() == self.base_sig
        viol = drc.new_violations(fl, ex, sorted(set(touched)), self.baseline) if self.check_rules else []
        legal = sig_ok and not viol
        c, terms = self.cost_fn(fl, ex, dict(zip([v.name for v in self.vars], x)))
        if not legal:
            c += self.penalty * (1 + len(viol))
        ev = Evaluation(list(x), c, terms, legal, len(viol), sig_ok, fl if keep else None, ex if keep else None)
        self.history.append(ev)
        return ev


def nelder_mead(f: Callable[[List[float]], float], x0: Sequence[float], step: Sequence[float],
                max_iter: int = 200, xtol: float = 1e-3, ftol: float = 1e-6,
                log: Optional[Callable[[int, float, List[float]], None]] = None) -> Tuple[List[float], float]:
    n = len(x0)
    pts = [list(x0)]
    for i in range(n):
        p = list(x0); p[i] += step[i]; pts.append(p)
    vals = [f(p) for p in pts]
    for it in range(max_iter):
        order = sorted(range(n + 1), key=lambda i: vals[i])
        pts = [pts[i] for i in order]; vals = [vals[i] for i in order]
        if log:
            log(it, vals[0], pts[0])
        if max(abs(pts[i][j] - pts[0][j]) for i in range(1, n + 1) for j in range(n)) < xtol \
                and abs(vals[-1] - vals[0]) < ftol:
            break
        cen = [sum(p[j] for p in pts[:-1]) / n for j in range(n)]
        worst = pts[-1]
        xr = [cen[j] + (cen[j] - worst[j]) for j in range(n)]
        fr = f(xr)
        if fr < vals[0]:
            xe = [cen[j] + 2 * (cen[j] - worst[j]) for j in range(n)]
            fe = f(xe)
            if fe < fr:
                pts[-1], vals[-1] = xe, fe
            else:
                pts[-1], vals[-1] = xr, fr
        elif fr < vals[-2]:
            pts[-1], vals[-1] = xr, fr
        else:
            xc = [cen[j] + 0.5 * (worst[j] - cen[j]) for j in range(n)]
            fc = f(xc)
            if fc < vals[-1]:
                pts[-1], vals[-1] = xc, fc
            else:                                   # shrink
                for i in range(1, n + 1):
                    pts[i] = [pts[0][j] + 0.5 * (pts[i][j] - pts[0][j]) for j in range(n)]
                    vals[i] = f(pts[i])
    i = min(range(n + 1), key=lambda k: vals[k])
    return pts[i], vals[i]


def solve(problem: Problem, max_iter: int = 200, step_frac: float = 0.25,
          verbose: bool = True) -> Evaluation:
    x0 = [v.x0 for v in problem.vars]
    step = [max((v.hi - v.lo) * step_frac, 1e-3) for v in problem.vars]
    best: Dict[str, Evaluation] = {}

    def f(x):
        ev = problem.evaluate(x)
        if "b" not in best or ev.cost < best["b"].cost:
            best["b"] = ev
        return ev.cost

    def log(it, val, x):
        if verbose and (it % 10 == 0):
            print("  iter %3d  cost %.6g  x=%s" % (it, val, ["%.3f" % v for v in x]))

    x, val = nelder_mead(f, x0, step, max_iter=max_iter, log=log)
    return problem.evaluate(x, keep=True)


# ---------------------------------------------------------------------------
# Discrete moves (fingers): greedy coordinate search over integer states
# ---------------------------------------------------------------------------

@dataclass
class IntVariable:
    name: str
    lo: int
    hi: int
    x0: int
    apply: Callable[[FlatLayout, "extract.Extraction", int], List[int]]   # rebuilds state from the BASE layout


class DiscreteProblem:
    """Like Problem, but each variable is an integer (e.g. a finger count) and
    the moves are re-applied from the base layout for every state, because
    geometry-generating moves are not reversible edits."""

    def __init__(self, base: FlatLayout, tech: Tech, variables: Sequence[IntVariable], cost, labels=None,
                 illegal_penalty: float = 1e3):
        self.base, self.tech, self.vars, self.cost_fn, self.labels, self.penalty = base, tech, list(variables), cost, labels, illegal_penalty
        self.base_ex = extract.extract(base, tech, labels)
        self.base_sig = self.base_ex.signature()
        self.baseline = {drc.key(v) for v in drc.check(base, self.base_ex)}
        self.cache: Dict[Tuple[int, ...], Evaluation] = {}

    def evaluate(self, x: Sequence[int], keep: bool = False) -> Evaluation:
        key = tuple(int(v) for v in x)
        if key in self.cache and not keep:
            return self.cache[key]
        fl = copy.deepcopy(self.base)
        touched: List[int] = []
        legal = True
        ex = self.base_ex
        deleted = False
        for v, var in zip(key, self.vars):
            n0 = len(fl.rects)
            try:
                t = var.apply(fl, ex, v)
            except Exception as e:                      # a move that cannot be made
                legal = False; t = []
            if any(i >= len(fl.rects) for i in t) or len(fl.rects) < n0 + len([i for i in t if i >= n0]):
                deleted = True                           # a move removed rects: earlier ids are stale
            touched += t
            if t:
                ex = extract.extract(fl, self.tech, self.labels)   # later moves see the geometry so far
        ex = extract.extract(fl, self.tech, self.labels)
        sig_ok = ex.signature() == self.base_sig
        # after a deletion (remove_finger) ids have shifted: check the whole layout
        viol = drc.new_violations(fl, ex, None if deleted else sorted(set(touched)), self.baseline)
        legal = legal and sig_ok and not viol
        c, terms = self.cost_fn(fl, ex, dict(zip([v.name for v in self.vars], key)))
        if not legal:
            c += self.penalty * (1 + len(viol))
        ev = Evaluation(list(key), c, terms, legal, len(viol), sig_ok, fl if keep else None, ex if keep else None)
        self.cache[key] = ev
        return ev


def greedy_search(problem: DiscreteProblem, max_rounds: int = 20, verbose: bool = True) -> Evaluation:
    """Coordinate ascent: from the current state try +1/-1 on every variable,
    take the best improving legal neighbour, repeat until none improves."""
    x = [v.x0 for v in problem.vars]
    best = problem.evaluate(x)
    if verbose:
        print("  start  cost %.5g  %s" % (best.cost, dict(zip([v.name for v in problem.vars], x))))
    for rnd in range(max_rounds):
        cands = []
        for i, var in enumerate(problem.vars):
            for dlt in (+1, -1):
                y = list(x); y[i] += dlt
                if var.lo <= y[i] <= var.hi:
                    cands.append(problem.evaluate(y))
        cands = [c for c in cands if c.legal and c.cost < best.cost - 1e-9]
        if not cands:
            break
        best = min(cands, key=lambda c: c.cost); x = list(best.x)
        if verbose:
            print("  round %d  cost %.5g  %s  %s" % (rnd + 1, best.cost, dict(zip([v.name for v in problem.vars], x)),
                                                    {k: round(v, 3) for k, v in best.terms.items()}))
    return problem.evaluate(x, keep=True)
