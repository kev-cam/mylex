#!/usr/bin/env python3
"""Tier B review decoder: decode every dispatch packet and commit on all four
ports of the exec_top vectors (field order from ports_tierB.txt: inputs as
nibble-padded hex, outputs as binary), match FPU commits to their dispatch by
PC, check the FPU results against an exact IEEE-754 binary32 reference, and
tally coverage (op classes, rounding modes, special operands, latencies,
x bits in compared data).   usage: decode_tierB.py ports_tierB.txt vectors.txt
"""
import sys, os
from fractions import Fraction
from math import isqrt

PORTS, VEC = sys.argv[1], sys.argv[2]
ports = [(f[0], int(f[1]), f[2]) for f in (l.split() for l in open(PORTS)) if len(f) == 3 and f[2] != 'clk']
fields = [p for p in ports if p[0] == 'input'] + [p for p in ports if p[0] == 'output']
idx = {n: i for i, (_, _, n) in enumerate(fields)}
base = [16 if d == 'input' else 2 for (d, _, _) in fields]

def val(t, b):
    return None if ('x' in t.lower() or 'z' in t.lower()) else int(t, b)

rows, raw = [], []
for line in open(VEC):
    t = line.split()
    assert len(t) == len(fields), (len(t), len(fields))
    raw.append(t)
    rows.append([val(x, b) for x, b in zip(t, base)])

def bits(v, lo, w): return (v >> lo) & ((1 << w) - 1)

# dispatch_t (Tier B, 274 bits): eop0 sop1 rs3[2..65] rs2[66..129] rs1[130..193] op_args[194..220]
#   (fpu: fmt 194..195, frm 196..198) op_type[221..224] bytesel[225..228] rd[229..234]
#   wr_xregs[235..236] wb 237 PC[238..267] tmask[268..269] sid 270 cta 271 wis 272 uuid 273
def dec_disp(d):
    return dict(pc=bits(d, 238, 30), op=bits(d, 221, 4), fmt=bits(d, 194, 2), frm=bits(d, 196, 3),
                rd=bits(d, 229, 6), wb=bits(d, 237, 1), tmask=bits(d, 268, 2), wis=bits(d, 272, 1),
                a=[bits(d, 130, 32), bits(d, 162, 32)], b=[bits(d, 66, 32), bits(d, 98, 32)],
                c=[bits(d, 2, 32), bits(d, 34, 32)])
# commit_t (Tier B, 115 bits): eop0 sop1 data[2..65] bytesel[66..69] rd[70..75] wr_xregs[76..77]
#   wb 78 PC[79..108] tmask[109..110] sid 111 cta 112 wid 113 uuid 114
def dec_commit(d):
    return dict(pc=bits(d, 79, 30), rd=bits(d, 70, 6), wb=bits(d, 78, 1), tmask=bits(d, 109, 2),
                wid=bits(d, 113, 1), data=[bits(d, 2, 32), bits(d, 34, 32)])

OPN = {0: 'FADD', 1: 'FMUL', 2: 'FMADD', 3: 'FNMADD', 4: 'FDIV', 5: 'FSQRT', 8: 'F2I', 9: 'F2U',
       10: 'I2F', 11: 'U2F', 12: 'FCMP', 13: 'F2F', 14: 'FMISC'}
MISC = ['FSGNJ', 'FSGNJN', 'FSGNJX', 'FCLASS', 'FMV.X.W', 'FMV.W.X', 'FMIN', 'FMAX']
CMP = ['FLE', 'FLT', 'FEQ']
FRM = {0: 'RNE', 1: 'RTZ', 2: 'RDN', 3: 'RUP', 4: 'RMM', 7: 'DYN'}

def opname(p):
    o = p['op']
    if o == 14: return MISC[p['frm']]
    if o == 12: return CMP[p['frm']] if p['frm'] < 3 else 'FCMP?'
    n = OPN.get(o, 'op%d' % o)
    if o == 0 and p['fmt'] & 2: n = 'FSUB'
    if o == 2 and p['fmt'] & 2: n = 'FMSUB'
    if o == 3 and p['fmt'] & 2: n = 'FNMSUB'
    return n

# ----------------------------------------------------------------- IEEE reference
QNAN = 0x7FC00000
def f32_class(x):
    s, e, m = x >> 31, (x >> 23) & 0xFF, x & 0x7FFFFF
    if e == 0xFF: return 'nan' if m else 'inf', s
    if e == 0: return ('zero' if m == 0 else 'sub'), s
    return 'norm', s
def is_snan(x): return f32_class(x)[0] == 'nan' and not (x & 0x400000)
def f32_val(x):
    k, s = f32_class(x)
    e, m = (x >> 23) & 0xFF, x & 0x7FFFFF
    if k == 'zero': return Fraction(0)
    if k == 'sub': v = Fraction(m, 1 << 149)
    else: v = Fraction((1 << 23) | m, 1 << 23) * (Fraction(2) ** (e - 127))
    return -v if s else v

def round_f32(x, rm, zsign=0):
    """exact rational -> (bits, inexact). zsign: sign of an exact-zero result."""
    if x == 0:
        return (0x80000000 if zsign else 0), False
    s = 1 if x < 0 else 0
    a = -x if s else x
    n, d = a.numerator, a.denominator
    e = n.bit_length() - d.bit_length()
    if Fraction(n, d) < Fraction(2) ** e: e -= 1          # 2^e <= a < 2^(e+1)
    q = Fraction(2) ** (max(e, -126) - 23)                 # quantum (subnormal floor at 2^-149)
    m, rem = divmod(a.numerator * q.denominator, a.denominator * q.numerator)
    inexact = rem != 0
    half = 2 * rem - a.denominator * q.numerator          # sign of (rem - q/2) numerator-scaled
    up = False
    if inexact:
        if rm == 0: up = half > 0 or (half == 0 and (m & 1))
        elif rm == 1: up = False
        elif rm == 2: up = s == 1
        elif rm == 3: up = s == 0
        elif rm == 4: up = half >= 0
    if up: m += 1
    ee = max(e, -126)
    if m == (1 << 24): m >>= 1; ee += 1
    if m < (1 << 23):  # subnormal
        return (s << 31) | m, inexact
    if ee > 127:
        if rm == 1 or (rm == 2 and s == 0) or (rm == 3 and s == 1): return (s << 31) | 0x7F7FFFFF, True
        return (s << 31) | 0x7F800000, True
    return (s << 31) | ((ee + 127) << 23) | (m & 0x7FFFFF), inexact

def fma_ref(a, b, c, neg_prod, neg_c, rm, mul_only=False, add_only=False):
    """result bits of (+-)(a*b) (+-) c; add_only: a + (+-)b (c unused); mul_only: a*b"""
    ops = [a, b] if mul_only else ([a, b] if add_only else [a, b, c])
    ka, sa = f32_class(a); kb, sb = f32_class(b); kc, sc = f32_class(c)
    if any(f32_class(o)[0] == 'nan' for o in ops): return QNAN
    if add_only:
        x, y = f32_val(a), (-f32_val(b) if neg_c else f32_val(b)); sy = sb ^ neg_c
        if ka == 'inf' and kb == 'inf': return (sa << 31) | 0x7F800000 if sa == sy else QNAN
        if ka == 'inf': return a
        if kb == 'inf': return (sy << 31) | 0x7F800000
        r = x + y
        return round_f32(r, rm, zsign=(sa & sy) if (ka == 'zero' and kb == 'zero') else (1 if rm == 2 else 0))[0] if r == 0 else round_f32(r, rm)[0]
    # product
    if (ka == 'inf' and kb == 'zero') or (kb == 'inf' and ka == 'zero'): return QNAN
    sp = sa ^ sb ^ neg_prod
    if ka == 'inf' or kb == 'inf':
        if mul_only: return (sp << 31) | 0x7F800000
        if kc == 'inf' and (sc ^ neg_c) != sp: return QNAN
        return (sp << 31) | 0x7F800000
    p = f32_val(a) * f32_val(b)
    if neg_prod: p = -p
    if mul_only:
        return round_f32(p, rm, zsign=sp)[0]
    if kc == 'inf': return ((sc ^ neg_c) << 31) | 0x7F800000
    cv = -f32_val(c) if neg_c else f32_val(c); scv = sc ^ neg_c
    r = p + cv
    if r == 0:
        if p == 0 and cv == 0: z = sp & scv if sp != scv else sp
        else: z = 1 if rm == 2 else 0
        if p == 0 and cv == 0 and sp != scv: z = 1 if rm == 2 else 0
        return round_f32(r, rm, zsign=z)[0]
    return round_f32(r, rm)[0]

def div_ref(a, b, rm):
    ka, sa = f32_class(a); kb, sb = f32_class(b); s = sa ^ sb
    if ka == 'nan' or kb == 'nan': return QNAN
    if ka == 'inf' and kb == 'inf': return QNAN
    if ka == 'zero' and kb == 'zero': return QNAN
    if ka == 'inf' or kb == 'zero': return (s << 31) | 0x7F800000
    if kb == 'inf' or ka == 'zero': return s << 31
    return round_f32(f32_val(a) / f32_val(b), rm)[0]

def sqrt_ref(a, rm):
    ka, sa = f32_class(a)
    if ka == 'nan': return QNAN
    if ka == 'zero': return a
    if sa: return QNAN
    if ka == 'inf': return a
    v = f32_val(a); K = 300
    n = v.numerator * v.denominator * (1 << (2 * K))
    r = isqrt(n); exact = r * r == n
    approx = Fraction(r, v.denominator << K)
    if not exact: approx += Fraction(1, 1 << (2 * K))   # sticky: strictly above the floor
    return round_f32(approx, rm)[0]

def round_int(v, rm):
    fl = v.numerator // v.denominator; rem = v - fl
    if rem == 0: return fl
    if rm == 0: return fl + (1 if rem > Fraction(1, 2) or (rem == Fraction(1, 2) and fl % 2) else 0)
    if rm == 1: return fl if v >= 0 else fl + 1
    if rm == 2: return fl
    if rm == 3: return fl + 1
    if rm == 4: return fl + (1 if rem >= Fraction(1, 2) else 0) if v >= 0 else fl + (1 if rem > Fraction(1, 2) else 0)

def f2i_ref(a, rm, unsigned):
    k, s = f32_class(a)
    if k == 'nan': return 0xFFFFFFFF if unsigned else 0x7FFFFFFF
    if k == 'inf': return (0xFFFFFFFF if not s else 0) if unsigned else (0x7FFFFFFF if not s else 0x80000000)
    i = round_int(f32_val(a), rm)
    if unsigned:
        if i < 0: return 0
        if i > 0xFFFFFFFF: return 0xFFFFFFFF
        return i
    if i > 0x7FFFFFFF: return 0x7FFFFFFF
    if i < -0x80000000: return 0x80000000
    return i & 0xFFFFFFFF

def i2f_ref(a, rm, unsigned):
    i = a if unsigned else (a - (1 << 32) if a & 0x80000000 else a)
    return round_f32(Fraction(i), rm)[0]

def minmax_ref(a, b, is_max):
    ka, sa = f32_class(a); kb, sb = f32_class(b)
    if ka == 'nan' and kb == 'nan': return QNAN
    if ka == 'nan': return b
    if kb == 'nan': return a
    va, vb = f32_val(a), f32_val(b)
    if va == vb:  # zeros of both signs: -0 < +0
        if is_max: return a if sa == 0 else b
        return a if sa == 1 else b
    if is_max: return a if va > vb else b
    return a if va < vb else b

def class_ref(a):
    k, s = f32_class(a)
    if k == 'nan': return 0x100 if is_snan(a) else 0x200
    return {('inf', 1): 1, ('norm', 1): 2, ('sub', 1): 4, ('zero', 1): 8,
            ('zero', 0): 0x10, ('sub', 0): 0x20, ('norm', 0): 0x40, ('inf', 0): 0x80}[(k, s)]

def cmp_ref(a, b, which):
    if f32_class(a)[0] == 'nan' or f32_class(b)[0] == 'nan': return 0
    va, vb = f32_val(a), f32_val(b)
    return int([va <= vb, va < vb, va == vb][which])

def ref(p, lane, frm_eff):
    a, b, c = p['a'][lane], p['b'][lane], p['c'][lane]
    o, fmt, frm = p['op'], p['fmt'], frm_eff
    if o == 0: return fma_ref(a, b, 0, 0, bool(fmt & 2), frm, add_only=True)
    if o == 1: return fma_ref(a, b, 0, 0, 0, frm, mul_only=True)
    if o == 2: return fma_ref(a, b, c, 0, bool(fmt & 2), frm)
    if o == 3: return fma_ref(a, b, c, 1, not bool(fmt & 2), frm)
    if o == 4: return div_ref(a, b, frm)
    if o == 5: return sqrt_ref(a, frm)
    if o == 8: return f2i_ref(a, frm, False)
    if o == 9: return f2i_ref(a, frm, True)
    if o == 10: return i2f_ref(a, frm, False)
    if o == 11: return i2f_ref(a, frm, True)
    if o == 12: return cmp_ref(a, b, p['frm'])
    if o == 14:
        m = p['frm']
        if m == 0: return (a & 0x7FFFFFFF) | (b & 0x80000000)
        if m == 1: return (a & 0x7FFFFFFF) | ((~b) & 0x80000000)
        if m == 2: return a ^ (b & 0x80000000)
        if m == 3: return class_ref(a)
        if m == 4: return a
        if m == 5: return a
        if m == 6: return minmax_ref(a, b, False)
        if m == 7: return minmax_ref(a, b, True)
    return None

# ----------------------------------------------------------------- walk the vectors
disp = {u: {} for u in range(4)}          # port -> pc -> (cycle, packet)
commits = {u: [] for u in range(4)}
frm_csr = {0: 0, 1: 0}                    # per-warp FRM as programmed through the SFU stream (decoded below)
sfu_frm_writes = []
n = len(rows)
disp_fire = [0] * 4; disp_stall = [0] * 4; com = [0] * 4; com_bp = [0] * 4
xbits_valid = 0; xbits_valid_masked = 0; xrows = 0
for c, r in enumerate(rows):
    for u in range(4):
        v, rd = r[idx['dispatch_if_%d_valid' % u]], r[idx['dispatch_if_%d_ready' % u]]
        if v == 1 and rd == 0: disp_stall[u] += 1
        if v == 1 and rd == 1:
            disp_fire[u] += 1
            p = dec_disp(r[idx['dispatch_if_%d_data' % u]])
            disp[u].setdefault(p['pc'], []).append((c, p))
            if u == 2 and p['op'] in (0, 1, 2, 3):   # csr op: addr in op_args bits? decoded loosely below
                pass
        cv, cr = r[idx['commit_if_%d_valid' % u]], r[idx['commit_if_%d_ready' % u]]
        if cv == 1 and cr == 0: com_bp[u] += 1
        if cv == 1 and cr == 1:
            com[u] += 1
            tok = raw[c][idx['commit_if_%d_data' % u]]
            d = r[idx['commit_if_%d_data' % u]]
            if u == 3:
                nx = tok.count('x') + tok.count('X')
                if nx: xrows += 1
                xbits_valid += nx
                # x bits inside the data lanes selected by tmask (bit i of the token string = position len-1-i)
                if d is None:
                    L = len(tok)
                    tm = int(tok[L - 1 - 110: L - 109], 2) if 'x' not in tok[L - 1 - 110: L - 109] else 3
                    for lane in range(2):
                        if tm >> lane & 1:
                            seg = tok[L - 1 - (33 + 32 * lane): L - (2 + 32 * lane)]
                            xbits_valid_masked += seg.count('x')
                    commits[u].append((c, None, tok))
                else:
                    commits[u].append((c, dec_commit(d), tok))
            else:
                commits[u].append((c, dec_commit(d) if d is not None else None, tok))

print("cycles: %d   dispatch fires alu/lsu/sfu/fpu = %s (stalls %s)   commits = %s (backpressure cycles %s)"
      % (n, '/'.join(map(str, disp_fire)), '/'.join(map(str, disp_stall)), '/'.join(map(str, com)), '/'.join(map(str, com_bp))))
print("FPU commits with any x in commit_if_3_data: %d rows, %d x bits total, %d x bits inside tmask'd data lanes"
      % (xrows, xbits_valid, xbits_valid_masked))

# SFU stream: FRM write is the first SFU dispatch (CSRRW imm) -- find CSR writes to 0x002 via op_args
# csr_args_t: {padding, use_imm(1), addr(12), imm5(5)} at op_args[194..]: imm5 = 194..198, addr = 199..210, use_imm = 211
for pc, lst in sorted(disp[2].items()):
    for (c, p) in lst:
        d = None
for c, r in enumerate(rows):
    if r[idx['dispatch_if_2_valid']] == 1 and r[idx['dispatch_if_2_ready']] == 1:
        d = r[idx['dispatch_if_2_data']]
        addr = bits(d, 199, 12); imm5 = bits(d, 194, 5); use_imm = bits(d, 211, 1); op = bits(d, 221, 4); wis = bits(d, 272, 1)
        if addr in (1, 2, 3) and bits(d, 238, 30) >= 0x300 and bits(d, 238, 30) < 0x400:
            sfu_frm_writes.append((c, op, use_imm, addr, imm5, wis))
print("SFU dispatches touching fflags/frm/fcsr (cycle, op, use_imm, addr, imm5, wis): %s" % sfu_frm_writes)
if sfu_frm_writes and sfu_frm_writes[0][1] == 6 and sfu_frm_writes[0][3] == 2:   # CSRRW frm
    frm_csr[sfu_frm_writes[0][5]] = sfu_frm_writes[0][4]
print("FRM per warp assumed for DYN: %s" % frm_csr)

# ----------------------------------------------------------------- FPU commit decode + reference check
print("\n=== FPU commits (cycle, PC, op, frm, wid, tmask, rd, lane results ; reference) ===")
opcount = {}; frmcount = {}; specials = {}; lat = {}; mism = 0; checked = 0; ooo = 0
last_disp_c = -1
seen_pc = set()
for (c, k, tok) in commits[3]:
    if k is None:
        print("%4d FPU commit with x in header fields: %s" % (c, tok[:40])); continue
    pc = k['pc']; hits = disp[3].get(pc)
    if not hits:
        print("%4d FPU commit PC=%03x has NO matching dispatch" % (c, pc)); continue
    dc, p = hits[0]
    if dc < last_disp_c: ooo += 1
    last_disp_c = dc
    seen_pc.add(pc)
    nm = opname(p); opcount[nm] = opcount.get(nm, 0) + 1
    frm_eff = p['frm']
    arith = p['op'] in (0, 1, 2, 3, 4, 5, 8, 9, 10, 11)
    if arith:
        f = FRM.get(p['frm'], '?')
        if p['frm'] == 7: f = 'DYN->' + FRM.get(frm_csr[p['wis']], '?'); frm_eff = frm_csr[p['wis']]
        frmcount[f] = frmcount.get(f, 0) + 1
    lat.setdefault(nm, []).append(c - dc)
    res = []; refs = []
    for lane in range(2):
        if not (p['tmask'] >> lane & 1): res.append('--------'); refs.append('--------'); continue
        # operand specials
        for o in ([p['a'][lane]] + ([p['b'][lane]] if p['op'] in (0, 1, 2, 3, 4, 12, 14) else []) + ([p['c'][lane]] if p['op'] in (2, 3) else [])):
            if p['op'] in (10, 11): break
            kk, ss = f32_class(o)
            key = {'nan': ('sNaN' if is_snan(o) else 'qNaN'), 'inf': ('-inf' if ss else '+inf'), 'zero': ('-0' if ss else '+0'), 'sub': ('-sub' if ss else '+sub'), 'norm': 'normal'}[kk]
            specials[key] = specials.get(key, 0) + 1
        rv = ref(p, lane, frm_eff)
        got = k['data'][lane]
        res.append('%08x' % got)
        if rv is None: refs.append('????????')
        else:
            refs.append('%08x' % rv)
            checked += 1
            if rv != got: mism += 1; refs[-1] += '!'
    print("%4d PC=%03x %-8s frm=%d wid=%d tm=%s rd=%2d  %s %s ; ref %s %s   (disp @%d, lat %d)" % (
        c, pc, nm, p['frm'], k['wid'], format(k['tmask'], '02b'), k['rd'], res[1], res[0], refs[1], refs[0], dc, c - dc))

print("\n=== coverage ===")
print("FPU dispatched PCs: %d, committed: %d, missing commits: %s" % (len(disp[3]), len(seen_pc), sorted(set(disp[3]) - seen_pc)))
print("ops committed: %s" % ', '.join('%s x%d' % kv for kv in sorted(opcount.items())))
print("rounding modes (arith ops): %s" % ', '.join('%s x%d' % kv for kv in sorted(frmcount.items())))
print("operand classes seen (per lane operand): %s" % ', '.join('%s x%d' % kv for kv in sorted(specials.items())))
print("latency dispatch->commit per op: %s" % ', '.join('%s %s' % (k2, sorted(set(v))) for k2, v in sorted(lat.items())))
print("commits returned out of dispatch order: %d" % ooo)
print("reference check: %d lane results compared, %d mismatches" % (checked, mism))
# where in the run do the last FDIV/FSQRT commits fall
for nm in ('FDIV', 'FSQRT'):
    cs = [c for (c, k, tok) in commits[3] if k and disp[3].get(k['pc']) and opname(disp[3][k['pc']][0][1]) == nm]
    print("%s commits at cycles %s (run length %d)" % (nm, cs, n))
# tier A coverage (same tallies as coverage.py)
br = sum(1 for r in rows if r[idx['branch_ctl_if_0_valid']] == 1)
trap = sum(1 for r in rows if r[idx['sched_csr_if_trap_csr_wr_valid']] == 1)
cw = sum(1 for r in rows if r[idx['sched_csr_if_csr_wr_valid']] == 1)
w = {k2: sum(1 for r in rows if r[idx['warp_ctl_if_%s_valid' % k2]] == 1) for k2 in ['wspawn', 'tmc', 'split', 'sjoin', 'bar', 'wsync']}
reqs = sum(1 for r in rows if r[idx['lsu_client_if_0_req_valid']] == 1 and r[idx['lsu_client_if_0_req_ready']] == 1)
rsps = sum(1 for r in rows if r[idx['lsu_client_if_0_rsp_valid']] == 1 and r[idx['lsu_client_if_0_rsp_ready']] == 1)
dcr = sum(1 for r in rows if r[idx['dcr_csr_if_valid']] == 1 and r[idx['dcr_csr_if_ready']] == 1)
print("Tier A in this run: branches %d, csr_wr %d, trap_csr_wr %d, warp_ctl %s, lsu req/rsp %d/%d, dcr reads %d" % (br, cw, trap, w, reqs, rsps, dcr))
# SFU commits of the F CSR reads (PC >= 0x300): print the last few SFU commits with data
print("\n=== last SFU commits (F CSR read-back) ===")
for (c, k, tok) in commits[2][-7:]:
    if k: print("%4d PC=%03x wid=%d rd=%d data1=%08x data0=%08x" % (c, k['pc'], k['wid'], k['rd'], k['data'][1], k['data'][0]))
