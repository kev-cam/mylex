#!/usr/bin/env python3
"""c_expr -- B0 software frontend: a C expression subset -> expression DAG ->
one combinational Verilog module, conformant to the COMMON-BACKEND.md IR
contract (the module feeds the existing yosys producer recipes unchanged), plus
the M1-M5 metadata sidecar JSON.

SCOPE (COMMON-BACKEND.md section 3.1 / 3.3, build-order step B0): expressions
over fixed-width unsigned ints, single pure function, combinational only.
NOT here (deferred B1+): loops, control flow across statements, memory,
function calls, floating point.

ACCEPTED C SUBSET
  * one translation unit; the named function is compiled, the rest ignored
  * value parameters of type uint8_t / uint16_t / uint32_t  -> input ports
  * outputs: either  (a) return type uintN_t + a single `return expr;`
             -> one output port named `out`, or
             (b) void return + pointer parameters uintN_t *p, written once
             each via `*p = expr;`      -> one output port per pointer param
  * local declarations `uintN_t x = expr;` (const ok); plain re-assignment of
    locals is allowed (pure dataflow rebinding -- no control flow exists)
  * expressions: & | ^ ~ + - * << >> ! && || < > <= >= == != ?: casts to
    (uintN_t)/(unsigned)/(int), parentheses, integer constants
  * NO: / %, side effects (++/--/compound assign), pointers beyond out-params,
    arrays, calls, floats -- all rejected by name with the B-step that owns them

C SEMANTICS ARE THE SEMANTICS (the software oracle is the arbiter).  Integer
promotion is modeled faithfully: uint8_t/uint16_t promote to 32-bit int, so
0xFF + 0xFF is 0x1FE *before* the assignment back to a uint8_t output truncates
it to 0xFE, and ((a+b) >> 4) sees the 9-bit sum, not a masked 8-bit one.  The
emitter then NARROWS provably-safe widths on the way out (truncation commutes
with & | ^ ~ + - * <<; a value bound vmax makes zero-extension exact), which is
what lands the natural netlist shape ($add of width 8, not 32).  Where C's
semantics stop being representable in unsigned hardware the frontend REFUSES
loudly instead of guessing:
  * signed overflow (int arithmetic whose value bound exceeds INT_MAX) is UB
    in C -> rejected, with the cast that fixes it named
  * >> on a possibly-negative int is implementation-defined -> rejected
  * < <= > >= on a possibly-negative int would need a signed comparator ->
    rejected (B0 gap; == != are pattern-safe and allowed)
--naive-widths deliberately mis-models promotion (every op at its narrow
storage width -- the classic transliteration bug) so the test harness can
demonstrate that the oracle CATCHES it; never use it for real emission.

Usage:
  c_expr.py <src.c> <func> [-o out.v] [--meta out.meta.json]
      [--check N] [--seed S]      # software-oracle harness: gcc + iverilog
      [--workload JSON]           # M3 passthrough into the sidecar
      [--naive-widths]            # bug demonstrator (see above)
"""
import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE_LIBC = os.path.join(HERE, "fake_libc")

try:
    import pycparser
    from pycparser import c_ast
except ImportError:
    sys.exit("c_expr: pycparser is required (pip install pycparser)")

UINTS = {"uint8_t": 8, "uint16_t": 16, "uint32_t": 32,
         # the plain-C spellings of the same types
         "unsigned char": 8, "unsigned short": 16, "unsigned int": 32,
         "unsigned": 32}
INT_MAX = 2 ** 31 - 1
U32 = 2 ** 32


def die(msg, coord=None):
    sys.exit("c_expr: REJECT%s: %s" % (" at %s" % coord if coord else "", msg))


# ------------------------------------------------------------------ the DAG
class Node:
    """One value in the dataflow DAG, carrying its C-semantic bookkeeping.
    op      : 'in' | 'const' | 'not' | 'neg' | 'and' | 'or' | 'xor' | 'add' |
              'sub' | 'mul' | 'shl' | 'shr' | 'eq' | 'ne' | 'lt' | 'le' |
              'gt' | 'ge' | 'mux' | 'trunc'
    args    : child Node refs (or, for 'in': port name; 'const': value;
              'trunc': (child, width); shifts: (child, shamt-node-or-int))
    cwidth  : the C type width of the value (32 after promotion)
    signed  : C type signedness after promotion
    vmax    : max value bound as an unsigned cwidth-bit pattern (2^cwidth-1
              when unknown / possibly negative)
    neg     : True if the value, read as the signed C type, may be negative
              (i.e. the pattern may have the top bit set through all high bits)
    """
    __slots__ = ("op", "args", "cwidth", "signed", "vmax", "neg", "id")

    def __init__(self, op, args, cwidth, signed, vmax, neg):
        self.op, self.args, self.cwidth = op, args, cwidth
        self.signed, self.vmax, self.neg = signed, vmax, neg

    def maxbits(self):
        return max(1, self.vmax.bit_length())


class Dag:
    def __init__(self, naive=False):
        self.nodes = []          # creation order == topological order
        self.memo = {}           # hash-consing (CSE)
        self.naive = naive       # --naive-widths bug demonstrator

    def mk(self, op, args, cwidth, signed, vmax, neg):
        key = (op, tuple(id(a) if isinstance(a, Node) else a for a in args),
               cwidth, signed)
        if key in self.memo:
            return self.memo[key]
        n = Node(op, args, cwidth, signed, min(vmax, 2 ** cwidth - 1), neg)
        n.id = len(self.nodes)
        self.nodes.append(n)
        self.memo[key] = n
        return n

    # ---- leaves ----
    def inp(self, name, width):
        # value parameter: uintN.  Promotion: N<32 -> int (signed, 32);
        # N==32 -> unsigned int.  --naive-widths: stays at N (THE BUG).
        if self.naive:
            return self.mk("in", (name,), width, False, 2 ** width - 1, False)
        if width < 32:
            return self.mk("in", (name,), 32, True, 2 ** width - 1, False)
        return self.mk("in", (name,), 32, False, U32 - 1, False)

    def const(self, v, coord=None):
        if v < 0:
            die("negative constant %d (write it as an expression)" % v, coord)
        if v <= INT_MAX:
            return self.mk("const", (v,), 32, True, v, False)
        if v < U32:
            return self.mk("const", (v,), 32, False, v, False)
        die("constant %#x exceeds 32 bits (B0 is 32-bit max)" % v, coord)

    # ---- C usual arithmetic conversions over our (32-bit-capped) subset ----
    def _usual(self, a, b):
        signed = a.signed and b.signed
        return 32 if not self.naive else max(a.cwidth, b.cwidth), signed

    def binop(self, op, a, b, coord):
        w, signed = self._usual(a, b)
        ba = 2 ** w - 1 if a.neg else a.vmax     # pattern bound per operand
        bb = 2 ** w - 1 if b.neg else b.vmax
        if op == "and":
            return self.mk(op, (a, b), w, signed, min(ba, bb), a.neg and b.neg)
        if op in ("or", "xor"):
            neg = a.neg or b.neg
            vmax = 2 ** max(1, max(ba.bit_length(), bb.bit_length())) - 1
            return self.mk(op, (a, b), w, signed, vmax, neg)
        if op in ("add", "sub", "mul"):
            neg = a.neg or b.neg or (op == "sub" and signed and b.vmax > 0)
            v = ba + bb if op != "mul" else ba * bb
            if signed and not self.naive and not neg and v > INT_MAX:
                # int arithmetic: overflow is UB in C -- refuse, name the fix
                die("signed int %s may exceed INT_MAX (bound %#x) -- "
                    "undefined behavior in C; cast an operand to (uint32_t) "
                    "to make the wrap defined" % (op, v), coord)
            if op == "sub" and not signed:
                v = a.vmax if b.vmax == 0 else 2 ** w - 1   # unsigned wrap
            if v >= 2 ** w or neg:
                v = 2 ** w - 1
            return self.mk(op, (a, b), w, signed, v, neg)
        die("internal: binop %s" % op, coord)

    def shift(self, op, a, b, coord):
        w = a.cwidth if self.naive else 32
        signed = a.signed
        if b.op != "const":
            if b.neg or b.vmax >= w:
                die("shift amount not provably < %d" % w, coord)
        sh = b.args[0] if b.op == "const" else None
        if sh is not None and sh >= w:
            die("shift amount %d >= width %d" % (sh, w), coord)
        if op == "shl":
            if a.neg:
                die("<< on a possibly-negative int is UB in C", coord)
            v = a.vmax << (sh if sh is not None else 0)
            if signed and not self.naive and v > INT_MAX and sh is not None:
                die("signed int << overflows INT_MAX (bound %#x) -- UB in C; "
                    "cast the left operand to (uint32_t)" % v, coord)
            if sh is None or v >= 2 ** w:
                v = 2 ** w - 1
            return self.mk("shl", (a, b), w, signed, v, a.neg)
        # shr
        if signed and a.neg:
            die(">> on a possibly-negative int is implementation-defined in "
                "C -- cast the left operand to (uint32_t) first", coord)
        v = a.vmax >> sh if sh is not None else a.vmax
        return self.mk("shr", (a, b), w, signed, v, False)

    def cmp(self, op, a, b, coord):
        if op in ("lt", "le", "gt", "ge") and (a.neg or b.neg):
            die("ordered compare on a possibly-negative int needs a signed "
                "comparator -- not in B0; cast to (uint32_t) if the wrap "
                "semantics are what you mean", coord)
        if a.op == "const" and b.op == "const":
            # const-cmp-const: fold here, exactly as the C compiler already
            # folded it inside the oracle binary.  Both patterns are
            # non-negative VALUES (negative constants are rejected at the
            # leaf), so the plain integer compare IS the C compare for every
            # signedness mix the usual conversions produce (int/int signed
            # compare of non-negatives == unsigned compare == value compare).
            # The emitter stays correct if ever handed an unfolded one (its
            # compare width includes const maxbits -- it must not LIE), but
            # folding is what keeps a constant comparator out of the netlist.
            va, vb = a.args[0], b.args[0]
            res = {"eq": va == vb, "ne": va != vb, "lt": va < vb,
                   "le": va <= vb, "gt": va > vb, "ge": va >= vb}[op]
            return self.const(1 if res else 0, coord)
        return self.mk(op, (a, b), 32, True, 1, False)

    def mux(self, s, a, b, coord):
        w, signed = self._usual(a, b)
        neg = a.neg or b.neg
        vmax = 2 ** w - 1 if neg else max(a.vmax, b.vmax)
        return self.mk("mux", (s, a, b), w, signed, vmax, neg)

    def lnot(self, a):
        # via cmp() so !const folds like any other const-cmp-const
        return self.cmp("eq", a, self.const(0), None)

    def truthy(self, a):
        # via cmp() so const &&/||/?: conditions fold too
        return self.cmp("ne", a, self.const(0), None)

    def unop(self, op, a, coord):
        w = a.cwidth if self.naive else 32
        if op == "not":
            neg = not a.neg if a.signed else False
            vmax = 2 ** w - 1
            return self.mk("not", (a,), w, a.signed, vmax, a.signed and not a.neg)
        if op == "neg":
            if a.signed and not self.naive and a.vmax == 2 ** 31:
                die("-INT_MIN is UB", coord)
            neg = a.vmax > 0
            return self.mk("neg", (a,), w, a.signed, 2 ** w - 1 if neg else 0,
                           a.signed and neg)
        if op == "pos":
            return a
        die("internal: unop %s" % op, coord)

    def trunc(self, a, width):
        # (uintN_t) cast: value = a mod 2^N, then re-promotes as a uintN rvalue
        vmax = min(a.vmax, 2 ** width - 1) if not a.neg else 2 ** width - 1
        if self.naive:
            return self.mk("trunc", (a, width), width, False, vmax, False)
        if width < 32:
            return self.mk("trunc", (a, width), 32, True, vmax, False)
        return self.mk("trunc", (a, width), 32, False, vmax, False)

    def int_cast(self, a, coord):
        """`(int)` cast, modelled as C actually defines it (C17 6.3.1.3).

        Three cases, and the old code collapsed all three into "w = 32, value
        already fits", which was a SILENT WRONG ANSWER for the third:

        1. the operand is ALREADY an int (signed after promotion): the cast
           converts nothing, so pass the node through untouched -- crucially
           keeping `neg`, which is what makes the ordered-compare and signed
           `>>` refusals downstream still fire (`(int)(~a) < 1` refuses).
        2. the operand is unsigned but its value provably fits in INT_MAX:
           the conversion is value-preserving, so this is a pure RETYPE --
           same bit pattern, now marked signed so that later int arithmetic
           gets the INT_MAX overflow (UB) check it is entitled to.
        3. the operand may exceed INT_MAX (vmax > INT_MAX, or `neg` says the
           top bit may be set): the conversion is IMPLEMENTATION-DEFINED in C
           (6.3.1.3p3 -- gcc/clang wrap, so the value goes NEGATIVE).  B0
           refuses it by name, exactly as it already refuses signed overflow,
           signed `>>` and ordered signed compares.  Before this guard, such
           a value reached an ordered compare believed non-negative and was
           compared UNSIGNED: `(int)(a | 0x80000000u) < 1` is always 1 in C
           (negative < 1) and the emission said always 0 -- 259/259
           oracle-caught mismatches (examples/adv_intcast.c).
        """
        if a.signed and not self.naive:
            if not a.neg and a.vmax > INT_MAX:
                # unreachable by construction (the arithmetic paths refuse
                # signed bounds above INT_MAX and set neg when the top bit
                # can be set) -- but guard-or-die rather than trust it, since
                # the whole point of this branch is that a mis-set flag here
                # silently becomes an unsigned compare
                die("(int) cast of a signed value whose bound %#x exceeds "
                    "INT_MAX with neg unset -- width-model inconsistency, "
                    "refusing rather than guessing the compare signedness"
                    % a.vmax, coord)
            return a                       # int -> int: nothing converts
        if a.neg or a.vmax > INT_MAX:
            die("(int) cast of a value that may exceed INT_MAX (bound %#x) "
                "is an implementation-defined out-of-range conversion in C "
                "(C17 6.3.1.3p3: the result may be NEGATIVE) -- not in B0, "
                "because the negative value would then need a signed "
                "comparator/shifter; cast to (uint32_t) instead if unsigned "
                "wrap semantics are what you mean" % a.vmax, coord)
        return self.mk("trunc", (a, 32), 32, True, a.vmax, False)


# ------------------------------------------------------------- AST -> DAG
def typename_width(decl_type, coord):
    """IdentifierType/TypeDecl -> width, or None if not an accepted uint."""
    names = " ".join(decl_type.names) if hasattr(decl_type, "names") else ""
    return UINTS.get(names)


class FnCompiler(c_ast.NodeVisitor):
    def __init__(self, fdef, naive):
        self.dag = Dag(naive)
        self.env = {}                    # name -> Node (locals + params)
        self.inputs = []                 # (name, width) in signature order
        self.outputs = []                # (name, width) in signature order
        self.outval = {}                 # name -> Node
        self.fdef = fdef
        self.name = fdef.decl.name

    def compile(self):
        ftype = self.fdef.decl.type          # FuncDecl
        # ---- signature ----
        rett = ftype.type
        retw = typename_width(rett.type, rett.coord) \
            if isinstance(rett, c_ast.TypeDecl) else None
        is_void = (isinstance(rett, c_ast.TypeDecl)
                   and getattr(rett.type, "names", None) == ["void"])
        params = ftype.args.params if ftype.args else []
        for p in params:
            if isinstance(p.type, c_ast.PtrDecl):
                w = typename_width(p.type.type.type, p.coord)
                if w is None:
                    die("pointer param %s must be uint8_t*/uint16_t*/"
                        "uint32_t*" % p.name, p.coord)
                self.outputs.append((p.name, w))
            elif isinstance(p.type, c_ast.TypeDecl):
                w = typename_width(p.type.type, p.coord)
                if w is None:
                    die("param %s must be uint8_t/uint16_t/uint32_t"
                        % p.name, p.coord)
                self.inputs.append((p.name, w))
                self.env[p.name] = self.dag.inp(p.name, w)
            else:
                die("unsupported param kind for %s" % p.name, p.coord)
        if not is_void:
            if retw is None:
                die("return type must be void or uint8_t/uint16_t/uint32_t",
                    ftype.coord)
            if self.outputs:
                die("mix of return value and pointer outputs not in B0",
                    ftype.coord)
            self.outputs.append(("out", retw))
        if not self.outputs:
            die("no outputs: void function with no pointer out-params",
                ftype.coord)
        # ---- body ----
        for stmt in (self.fdef.body.block_items or []):
            self.stmt(stmt, retw if not is_void else None)
        missing = [n for n, _ in self.outputs if n not in self.outval]
        if missing:
            die("outputs never assigned: %s" % ", ".join(missing))
        return self

    def stmt(self, s, retw):
        if isinstance(s, c_ast.Decl):
            w = typename_width(s.type.type, s.coord) \
                if isinstance(s.type, c_ast.TypeDecl) else None
            if w is None:
                die("local %s must be uint8_t/uint16_t/uint32_t"
                    % getattr(s, "name", "?"), s.coord)
            if s.init is None:
                die("local %s declared without initializer (B0 is pure "
                    "dataflow)" % s.name, s.coord)
            # the declared type truncates+re-promotes, exactly like a cast
            self.env[s.name] = self.dag.trunc(self.expr(s.init), w)
        elif isinstance(s, c_ast.Assignment):
            if s.op != "=":
                die("compound assignment %s not in B0" % s.op, s.coord)
            v = self.expr(s.rvalue)
            lv = s.lvalue
            if isinstance(lv, c_ast.UnaryOp) and lv.op == "*" \
                    and isinstance(lv.expr, c_ast.ID):
                name = lv.expr.name
                ow = dict(self.outputs).get(name)
                if ow is None:
                    die("*%s is not a pointer out-param" % name, s.coord)
                if name in self.outval:
                    die("output *%s assigned twice" % name, s.coord)
                self.outval[name] = self.dag.trunc(v, ow)
            elif isinstance(lv, c_ast.ID):
                if lv.name not in self.env:
                    die("assignment to undeclared %s" % lv.name, s.coord)
                # sequential rebinding of a local (still pure dataflow);
                # its declared width keeps truncating, like C stores do
                self.env[lv.name] = self.dag.trunc(v, self._localw(lv.name))
            else:
                die("unsupported lvalue", s.coord)
        elif isinstance(s, c_ast.Return):
            if retw is None:
                die("return with value in a void function?", s.coord)
            if "out" in self.outval:
                die("multiple return statements (B0 has no control flow)",
                    s.coord)
            self.outval["out"] = self.dag.trunc(self.expr(s.expr), retw)
        else:
            die("statement %s not in B0 (loops/if are B1+/B3)"
                % type(s).__name__, getattr(s, "coord", None))

    def _localw(self, name):
        n = self.env[name]
        if n.op == "trunc":
            return n.args[1]
        die("internal: local %s has no declared width" % name)

    BIN = {"&": "and", "|": "or", "^": "xor", "+": "add", "-": "sub",
           "*": "mul", "<<": "shl", ">>": "shr"}
    CMP = {"==": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}

    def expr(self, e):
        d = self.dag
        if isinstance(e, c_ast.ID):
            if e.name not in self.env:
                die("unknown identifier %s" % e.name, e.coord)
            return self.env[e.name]
        if isinstance(e, c_ast.Constant):
            if e.type not in ("int", "unsigned int", "long int",
                              "unsigned long int", "char"):
                die("constant type %s not in B0" % e.type, e.coord)
            txt = e.value.rstrip("uUlL")
            return d.const(int(txt, 0), e.coord)
        if isinstance(e, c_ast.UnaryOp):
            if e.op == "~":
                return d.unop("not", self.expr(e.expr), e.coord)
            if e.op == "-":
                return d.unop("neg", self.expr(e.expr), e.coord)
            if e.op == "+":
                return self.expr(e.expr)
            if e.op == "!":
                return d.lnot(self.expr(e.expr))
            die("unary %s not in B0" % e.op, e.coord)
        if isinstance(e, c_ast.BinaryOp):
            if e.op in self.BIN:
                a, b = self.expr(e.left), self.expr(e.right)
                if e.op in ("<<", ">>"):
                    return d.shift(self.BIN[e.op], a, b, e.coord)
                return d.binop(self.BIN[e.op], a, b, e.coord)
            if e.op in self.CMP:
                return d.cmp(self.CMP[e.op], self.expr(e.left),
                             self.expr(e.right), e.coord)
            if e.op == "&&":
                return d.mk("and", (d.truthy(self.expr(e.left)),
                                    d.truthy(self.expr(e.right))),
                            32, True, 1, False)
            if e.op == "||":
                return d.mk("or", (d.truthy(self.expr(e.left)),
                                   d.truthy(self.expr(e.right))),
                            32, True, 1, False)
            if e.op in ("/", "%"):
                die("division/modulo not in B0 (no measured mapping)", e.coord)
            die("binary %s not in B0" % e.op, e.coord)
        if isinstance(e, c_ast.TernaryOp):
            return d.mux(d.truthy(self.expr(e.cond)),
                         self.expr(e.iftrue), self.expr(e.iffalse), e.coord)
        if isinstance(e, c_ast.Cast):
            w = typename_width(e.to_type.type.type, e.coord) \
                if isinstance(e.to_type.type, c_ast.TypeDecl) else None
            if w is None:
                names = []
                try:
                    names = e.to_type.type.type.names
                except AttributeError:
                    pass
                if names == ["int"]:
                    # NOT d.trunc(...,32): an (int) cast is a SIGNED retype,
                    # and above INT_MAX it is implementation-defined -- see
                    # Dag.int_cast (the guard that closes the silent unsigned
                    # compare, examples/adv_intcast.c)
                    return d.int_cast(self.expr(e.expr), e.coord)
                die("cast to unsupported type", e.coord)
            return d.trunc(self.expr(e.expr), w)
        die("expression %s not in B0" % type(e).__name__,
            getattr(e, "coord", None))


# --------------------------------------------------- DAG -> Verilog (emit)
def emit_verilog(fc, src_path, naive):
    """Backward demanded-width pass, then one wire+assign per live DAG node.
    Width law: emit_w = max(1, min(demand, maxbits, cwidth)) -- truncation
    commutes with & | ^ ~ + - * <<, and a vmax bound makes zero-extension
    exact, so this is semantics-preserving BY CONSTRUCTION (>> by a constant
    is emitted as a slice of a (demand+k)-wide operand; compares are emitted
    at full operand width)."""
    dag = fc.dag
    demand = {}                          # node id -> demanded LSB count

    def ask(n, d):
        demand[n.id] = max(demand.get(n.id, 0), min(d, n.cwidth))

    roots = [(name, w, fc.outval[name]) for name, w in fc.outputs]
    for _, w, n in roots:
        ask(n, w)
    for n in reversed(dag.nodes):
        d = demand.get(n.id)
        if d is None:
            continue
        # cap at the node's own provable width: bits above maxbits are zero
        # (consumers zero-extend), so never demand them from the children
        d = min(d, n.cwidth if n.neg else max(1, n.maxbits()))
        if n.op in ("and", "or", "xor", "add", "sub", "mul"):
            ask(n.args[0], d), ask(n.args[1], d)
        elif n.op in ("not", "neg"):
            ask(n.args[0], d)
        elif n.op == "shl":
            a, b = n.args
            ask(a, d)
            if b.op != "const":
                ask(b, b.maxbits())
        elif n.op == "shr":
            a, b = n.args
            if b.op == "const":
                ask(a, min(d + b.args[0], a.cwidth))
            else:
                ask(a, a.cwidth if a.neg else a.maxbits())
                ask(b, b.maxbits())
        elif n.op in ("eq", "ne", "lt", "le", "gt", "ge"):
            a, b = n.args
            cw = max(a.cwidth, b.cwidth) if (a.neg or b.neg) \
                else max(a.maxbits(), b.maxbits())
            ask(a, cw), ask(b, cw)
        elif n.op == "mux":
            s, a, b = n.args
            ask(s, 1), ask(a, d), ask(b, d)
        elif n.op == "trunc":
            ask(n.args[0], min(d, n.args[1]))
        # 'in' / 'const': leaves

    def emit_w(n):
        d = demand[n.id]
        mb = n.cwidth if n.neg else n.maxbits()
        return max(1, min(d, mb, n.cwidth))

    names, lines, emit_w_of_text = {}, [], {}

    def ref(n, ctxw=None):
        """Verilog text for node n in a ctxw-wide context (Verilog zero-
        extends narrower unsigned operands in context; wider never happens
        for value-carrying ops because emit widths are demand-capped, and
        where it can (shared child), low-bit truncation is the C meaning)."""
        if n.op == "const":
            w = ctxw or max(1, n.args[0].bit_length())
            return "%d'h%x" % (w, n.args[0] & ((1 << w) - 1))
        if n.op == "in":
            w = emit_w(n)
            src = n.args[0]
            iw = dict(fc.inputs)[src]
            return src if w >= iw else "%s[%d:0]" % (src, w - 1)
        return names[n.id]

    def slice_of(n, hi, lo, w):
        """bits [hi:lo] of node n as a w-wide value (n already emitted, or a
        leaf); Verilog forbids slicing a slice, so leaves are sliced at the
        base identifier and constants are folded."""
        if n.op == "const":
            return "%d'h%x" % (w, (n.args[0] >> lo) & ((1 << w) - 1))
        base = n.args[0] if n.op == "in" else names[n.id]
        basew = dict(fc.inputs)[n.args[0]] if n.op == "in" else emit_w(n)
        hi = min(hi, basew - 1)
        if lo > hi:
            return "%d'h0" % w
        if lo == 0 and hi == basew - 1:
            return base
        return "%s[%d:%d]" % (base, hi, lo)

    OPTXT = {"and": "&", "or": "|", "xor": "^", "add": "+", "sub": "-",
             "mul": "*", "eq": "==", "ne": "!=", "lt": "<", "le": "<=",
             "gt": ">", "ge": ">="}

    for n in dag.nodes:
        if n.id not in demand or n.op in ("in", "const"):
            continue
        w = emit_w(n)
        nm = "w%d" % n.id
        if n.op in ("and", "or", "xor", "add", "sub", "mul"):
            rhs = "%s %s %s" % (ref(n.args[0], w), OPTXT[n.op], ref(n.args[1], w))
        elif n.op == "not":
            rhs = "~%s" % ref(n.args[0], w)
        elif n.op == "neg":
            rhs = "-%s" % ref(n.args[0], w)
        elif n.op == "shl":
            a, b = n.args
            rhs = "%s << %s" % (ref(a, w),
                                b.args[0] if b.op == "const" else ref(b))
        elif n.op == "shr":
            a, b = n.args
            if b.op == "const":
                k = b.args[0]
                rhs = slice_of(a, k + w - 1, k, w)
            else:
                rhs = "%s >> %s" % (ref(a), ref(b))
        elif n.op in ("eq", "ne", "lt", "le", "gt", "ge"):
            a, b = n.args
            # the compare width must cover BOTH sides' provable bits: a const
            # comparand counts at its full maxbits (NOT 1 -- ref() masks the
            # constant to cw, so understating it miscompares: `0xF == 1`
            # became `1'h1 == 1'h1`, and `(a & 0xF) == 0x10` became
            # `w == 4'h0`; see examples/cmp_precedence_trap.c and
            # examples/cmp_wide_const.c).  Dag.cmp folds const-cmp-const
            # before it ever gets here, but the emitter must not lie if
            # handed one, so consts take maxbits on this path too.
            cw = max(emit_w(a) if a.op != "const" else a.maxbits(),
                     emit_w(b) if b.op != "const" else b.maxbits())
            rhs = "%s %s %s" % (ref(a, cw), OPTXT[n.op], ref(b, cw))
        elif n.op == "mux":
            s, a, b = n.args
            rhs = "%s ? %s : %s" % (ref(s, 1), ref(a, w), ref(b, w))
        elif n.op == "trunc":
            a, tw = n.args
            if a.op == "const":
                rhs = "%d'h%x" % (w, a.args[0] & ((1 << w) - 1))
            elif emit_w(a) <= w:
                rhs = ref(a, w)
            else:
                rhs = slice_of(a, w - 1, 0, w)
        else:
            die("internal: emit %s" % n.op)
        # a bare-identifier rhs is a pure alias: reference it directly instead
        # of minting a dead wire (keeps the mapped netlist byte-identical to
        # the RTL-origin one -- aliases otherwise survive as top-level wires)
        if re.match(r"^[A-Za-z_]\w*$", rhs) and emit_w_of_text.get(rhs, w) == w:
            names[n.id] = rhs
            continue
        names[n.id] = nm
        emit_w_of_text[nm] = w
        lines.append("  wire [%d:0] %s = %s;" % (w - 1, nm, rhs))

    ports = ["  input  [%d:0] %s" % (w - 1, nm) for nm, w in fc.inputs] + \
            ["  output [%d:0] %s" % (w - 1, nm) for nm, w in fc.outputs]
    outs = []
    for nm, w in fc.outputs:
        n = fc.outval[nm]
        if n.op == "const":
            r = "%d'h%x" % (w, n.args[0] & ((1 << w) - 1))
        else:
            ew = emit_w(n)
            r = ref(n, w) if n.op == "in" else names[n.id]
            if ew < w:
                r = "{%d'h0, %s}" % (w - ew, r)
            elif ew > w:
                r = slice_of(n, w - 1, 0, w)
        outs.append("  assign %s = %s;" % (nm, r))
    # merge single-use root wires into the output assigns (`wire w10 = X ^ Y;
    # assign maj = w10;` -> `assign maj = X ^ Y;`): the extra net name would
    # otherwise survive synthesis as a dead top-level alias of the output
    for i, o in enumerate(outs):
        m = re.match(r"  assign (\w+) = (w\d+);$", o)
        if not m:
            continue
        port, wn = m.groups()
        alltxt = "\n".join([ln for ln in lines if ln is not None]
                           + outs[:i] + outs[i + 1:])
        if len(re.findall(r"\b%s\b" % wn, alltxt)) != 1:
            continue                      # used elsewhere too -- keep the wire
        for j, ln in enumerate(lines):
            dm = ln and re.match(r"  wire \[\d+:0\] %s = (.*);$" % wn, ln)
            if dm:
                outs[i] = "  assign %s = %s;" % (port, dm.group(1))
                lines[j] = None
                break
    lines = [ln for ln in lines if ln is not None]
    hdr = ("// GENERATED by c_expr.py (B0 software frontend) from %s:%s\n"
           "// C semantics; promoted-width DAG, demand-narrowed emission.%s\n"
           % (os.path.basename(src_path), fc.name,
              "  ** NAIVE-WIDTHS BUG MODE -- DEMONSTRATOR ONLY **" if naive else ""))
    return (hdr
            + "module %s(\n%s\n);\n" % (fc.name, ",\n".join(ports))
            + "\n".join(lines) + ("\n" if lines else "")
            + "\n".join(outs) + "\nendmodule\n")


# ------------------------------------------------------------ oracle check
HARNESS = r"""
#include <stdio.h>
#include <stdint.h>
%s
int main(void) {
    %s
    while (scanf("%s"%s) == %d) {
        %s
        printf("%s\n"%s);
    }
    return 0;
}
"""


def oracle_check(fc, src, vfile, n_random, seed, workdir, exhaustive=False):
    """Compile the REAL C with gcc AND clang (the software oracle), simulate
    the emitted Verilog with iverilog on the same vectors, compare bit-exact.
    Vectors: corners (all-0, all-1s per input, 0xFF+0xFF style saturation)
    + n_random random.  Returns (nvec, mismatches, sample_lines, logs)."""
    ins, outs = fc.inputs, fc.outputs
    void_style = not (len(outs) == 1 and outs[0][0] == "out")
    # ---- C harness ----
    if void_style:
        callargs = ", ".join([nm for nm, _ in ins] + ["&%s" % nm for nm, _ in outs])
        decl = "".join("    uint%d_t %s;\n" % (w, nm) for nm, w in outs)
        call = "%s(%s);" % (fc.name, callargs)
    else:
        decl = "    uint%d_t out;\n" % outs[0][1]
        call = "out = %s(%s);" % (fc.name, ", ".join(nm for nm, _ in ins))
    scanf_fmt = " ".join("%x" for _ in ins)
    scanf_args = "".join(", &i_%s" % nm for nm, _ in ins)
    ivars = "".join("    unsigned i_%s;\n" % nm for nm, _ in ins)
    assigns = " ".join("uint%d_t %s = (uint%d_t)i_%s;" % (w, nm, w, nm)
                       for nm, w in ins)
    pf_fmt = " ".join("%x" for _ in outs)
    pf_args = "".join(", (unsigned)%s" % nm for nm, _ in outs)
    proto = open(src).read()
    csrc = HARNESS % ('#include "%s"' % os.path.abspath(src),
                      ivars + decl.rstrip(), scanf_fmt, scanf_args, len(ins),
                      assigns + " " + call, pf_fmt, pf_args)
    del proto
    cpath = os.path.join(workdir, fc.name + "_oracle.c")
    open(cpath, "w").write(csrc)
    logs = []
    for cc in ("gcc", "clang"):
        cmd = [cc, "-std=c11", "-Wall", "-O2", cpath, "-o",
               os.path.join(workdir, fc.name + "_oracle_" + cc)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        logs.append("$ " + " ".join(cmd) + (" -> OK" if r.returncode == 0
                                            else " -> FAIL\n" + r.stderr))
        if r.returncode:
            sys.exit("oracle compile failed:\n" + r.stderr)
    # ---- vectors ----
    rng = random.Random(seed)
    vecs = []
    zero = [0] * len(ins)
    ones = [(1 << w) - 1 for _, w in ins]
    vecs.append(zero)
    vecs.append(ones)                    # 0xFF+0xFF-style saturation corner
    for i in range(len(ins)):            # each input alone at all-ones
        v = list(zero)
        v[i] = ones[i]
        vecs.append(v)
    if exhaustive:
        total = 1
        for _, w in ins:
            total <<= w
        if total > 1 << 20:
            sys.exit("--exhaustive: input space 2^%d too large; use --check N"
                     % (total.bit_length() - 1))
        import itertools
        vecs += [list(v) for v in
                 itertools.product(*[range(1 << w) for _, w in ins])]
    for _ in range(n_random):
        vecs.append([rng.getrandbits(w) for _, w in ins])
    vtxt = "\n".join(" ".join("%x" % x for x in v) for v in vecs) + "\n"
    vpath = os.path.join(workdir, fc.name + "_vectors.txt")
    open(vpath, "w").write(vtxt)
    # ---- run C oracle ----
    gold = subprocess.run([os.path.join(workdir, fc.name + "_oracle_gcc")],
                          input=vtxt, capture_output=True, text=True).stdout
    gold2 = subprocess.run([os.path.join(workdir, fc.name + "_oracle_clang")],
                           input=vtxt, capture_output=True, text=True).stdout
    if gold != gold2:
        sys.exit("gcc and clang oracles DISAGREE -- the C source itself has "
                 "unspecified behavior; fix the source")
    # ---- Verilog TB ----
    tb = ["`timescale 1ns/1ps", "module tb;"]
    for nm, w in ins:
        tb.append("  reg [%d:0] %s;" % (w - 1, nm))
    for nm, w in outs:
        tb.append("  wire [%d:0] %s;" % (w - 1, nm))
    conn = ", ".join(".%s(%s)" % (nm, nm) for nm, _ in ins + outs)
    tb.append("  %s dut(%s);" % (fc.name, conn))
    tb.append("  integer fi, fo, r;")
    tb.append("  initial begin")
    tb.append('    fi = $fopen("%s", "r");' % vpath)
    tb.append('    fo = $fopen("%s", "w");' % os.path.join(workdir, fc.name + "_hw.txt"))
    fmt = " ".join("%h" for _ in ins)
    args = ", ".join(nm for nm, _ in ins)
    tb.append('    while ($fscanf(fi, "%s", %s) == %d) begin'
              % (fmt, args, len(ins)))
    tb.append("      #1;")
    ofmt = " ".join("%h" for _ in outs)
    oargs = ", ".join(nm for nm, _ in outs)
    tb.append('      $fwrite(fo, "%s\\n", %s);' % (ofmt, oargs))
    tb.append("    end")
    tb.append("    $fclose(fo); $finish;")
    tb.append("  end")
    tb.append("endmodule")
    tbpath = os.path.join(workdir, fc.name + "_tb.v")
    open(tbpath, "w").write("\n".join(tb) + "\n")
    sim = os.path.join(workdir, fc.name + "_sim")
    r = subprocess.run(["iverilog", "-g2012", "-o", sim, tbpath, vfile],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("iverilog failed:\n" + r.stderr)
    r = subprocess.run(["vvp", sim], capture_output=True, text=True)
    hw = open(os.path.join(workdir, fc.name + "_hw.txt")).read()

    def norm(txt):
        return [tuple(int(x, 16) for x in ln.split())
                for ln in txt.strip().splitlines() if ln.strip()]
    g, h = norm(gold), norm(hw)
    mism = []
    for i, (gv, hv) in enumerate(zip(g, h)):
        if gv != hv:
            mism.append((i, vecs[i], gv, hv))
    sample = []
    for i in (0, 1):                     # corners incl. the all-ones vector
        sample.append("vec %-4d in=%s  C=%s  HW=%s  %s"
                      % (i, " ".join("%02x" % x for x in vecs[i]),
                         " ".join("%x" % x for x in g[i]),
                         " ".join("%x" % x for x in h[i]),
                         "MATCH" if g[i] == h[i] else "** MISMATCH **"))
    return len(g), mism, sample, logs


# -------------------------------------------------------------------- main
def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("func")
    ap.add_argument("-o", "--out")
    ap.add_argument("--meta")
    ap.add_argument("--check", type=int, default=0,
                    help="run the gcc/clang-vs-iverilog oracle on N random "
                         "vectors (+ corners)")
    ap.add_argument("--exhaustive", action="store_true",
                    help="oracle over the FULL input space (<= 2^20 vectors)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workload", help="M3 passthrough: JSON workload vector "
                                       "or permodule reference")
    ap.add_argument("--naive-widths", action="store_true",
                    help="BUG DEMONSTRATOR: model every op at its narrow "
                         "storage width (ignores C integer promotion)")
    ar = ap.parse_args()

    # 0. the input artifact must be genuine C: real-compiler syntax gate
    r = subprocess.run(["gcc", "-std=c11", "-Wall", "-fsyntax-only", ar.src],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit("c_expr: gcc rejects the source (the artifact must be real "
                 "C):\n" + r.stderr)

    # 1. parse (pycparser; fake stdint.h for PARSING only)
    ast = pycparser.parse_file(ar.src, use_cpp=True, cpp_path="gcc",
                               cpp_args=["-E", "-P", "-nostdinc",
                                         "-I" + FAKE_LIBC])
    fdef = None
    for ext in ast.ext:
        if isinstance(ext, c_ast.FuncDef) and ext.decl.name == ar.func:
            fdef = ext
    if fdef is None:
        sys.exit("c_expr: no function definition '%s' in %s" % (ar.func, ar.src))

    # 2. compile + emit
    fc = FnCompiler(fdef, ar.naive_widths).compile()
    vtext = emit_verilog(fc, ar.src, ar.naive_widths)
    out = ar.out or os.path.splitext(os.path.basename(ar.src))[0] + ".v"
    open(out, "w").write(vtext)
    print("[c_expr] %s:%s -> %s  (%d inputs, %d outputs, %d DAG nodes)"
          % (ar.src, ar.func, out, len(fc.inputs), len(fc.outputs),
             len(fc.dag.nodes)))

    # 3. M1-M5 metadata sidecar (COMMON-BACKEND.md section 2.8)
    meta = {
        "M1_top": fc.name,
        "M1_ports": {nm: {"direction": "input", "width": w}
                     for nm, w in fc.inputs},
        "M2_clock": "none (combinational; zero clocks -- section 2.4)",
        "M3_workload": json.loads(ar.workload) if ar.workload else None,
        "M4_ackless_sidebands": [],
        "M5_provenance": {
            "producer": "c_expr.py B0 (mylex/nulex/frontends)",
            "producer_sha256": sha256(os.path.abspath(__file__)),
            "source": os.path.abspath(ar.src),
            "source_sha256": sha256(ar.src),
            "function": ar.func,
            "pycparser": pycparser.__version__,
            "naive_widths_bug_mode": bool(ar.naive_widths),
            "emitted_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "note": "level-profile shape is a synthesis choice, not a block "
                    "property (COMMON-BACKEND.md 2.8 M5): scores are "
                    "meaningful only against the netlist this producer made",
        },
    }
    for nm, w in fc.outputs:
        meta["M1_ports"][nm] = {"direction": "output", "width": w}
    mpath = ar.meta or out + ".meta.json"
    json.dump(meta, open(mpath, "w"), indent=1)
    print("[c_expr] metadata sidecar -> %s" % mpath)

    # 4. software oracle
    if ar.check or ar.exhaustive:
        wd = os.path.dirname(os.path.abspath(out)) or "."
        nv, mism, sample, logs = oracle_check(fc, ar.src, out, ar.check,
                                              ar.seed, wd, ar.exhaustive)
        for ln in logs:
            print("[oracle] " + ln)
        for ln in sample:
            print("[oracle] " + ln)
        if mism:
            print("[oracle] *** %d/%d MISMATCHES (first 5):" % (len(mism), nv))
            for i, v, gv, hv in mism[:5]:
                print("[oracle]   vec %d in=%s C=%s HW=%s"
                      % (i, ["%x" % x for x in v], gv, hv))
            sys.exit(1)
        print("[oracle] %d/%d vectors agree (gcc==clang==iverilog), 0 "
              "mismatches" % (nv, nv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
