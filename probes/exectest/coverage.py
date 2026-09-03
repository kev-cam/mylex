#!/usr/bin/env python3
"""Coverage tallies parsed from the oracle's vectors.txt (field order from
ports_tierA.txt: all inputs as nibble-padded hex, then all outputs as
binary, one character per bit -- see gen_tb.py).  A field with any x/z is None."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PORTS = os.path.join(HERE, 'ports_tierA.txt')
if not os.path.exists(PORTS):
    PORTS = os.path.join(HERE, '..', 'ports_tierA.txt')
VEC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'vectors.txt')

ports = []
for line in open(PORTS):
    f = line.split()
    if len(f) == 3 and f[2] != 'clk':
        ports.append((f[0], int(f[1]), f[2]))
fields = [p for p in ports if p[0] == 'input'] + [p for p in ports if p[0] == 'output']
idx = {n: i for i, (_, _, n) in enumerate(fields)}
base = [16 if d == 'input' else 2 for (d, _, _) in fields]

def val(tok, b):
    if 'x' in tok.lower() or 'z' in tok.lower():
        return None
    return int(tok, b)

rows = []
for line in open(VEC):
    t = line.split()
    if len(t) != len(fields):
        raise SystemExit("bad line: %d fields, expected %d" % (len(t), len(fields)))
    rows.append([val(x, b) for x, b in zip(t, base)])

def g(r, n):
    return r[idx[n]]

def bits(v, lo, w):
    return (v >> lo) & ((1 << w) - 1)

n = len(rows)
disp = [0, 0, 0]; disp_stall = [0, 0, 0]
commit = [0, 0, 0]; commit_bp = [0, 0, 0]
req_rd = req_wr = req_fence = req_stall = 0
byteen_hist = {}
mask_hist = {}
rsp = rsp_stall = 0
br = br_taken = br_trap = br_mret = 0
csr_wr = trap_wr = 0; trap_addrs = {}
wctl = dict(wspawn=0, tmc=0, split=0, sjoin=0, bar=0, wsync=0)
split_dvg = 0
dcr_reads = 0
drained_low = []; alm_low = []
bar_cycles = []; wsync_cycles = []
reset_release = None

for c, r in enumerate(rows):
    if reset_release is None and g(r, 'reset') == 0:
        reset_release = c
    for u in range(3):
        v = g(r, 'dispatch_if_%d_valid' % u); rd = g(r, 'dispatch_if_%d_ready' % u)
        if v == 1 and rd == 1: disp[u] += 1
        if v == 1 and rd == 0: disp_stall[u] += 1
        cv = g(r, 'commit_if_%d_valid' % u); cr = g(r, 'commit_if_%d_ready' % u)
        if cv == 1 and cr == 1: commit[u] += 1
        if cv == 1 and cr == 0: commit_bp[u] += 1
    rv = g(r, 'lsu_client_if_0_req_valid'); rr = g(r, 'lsu_client_if_0_req_ready')
    if rv == 1 and rr == 0: req_stall += 1
    if rv == 1 and rr == 1:
        d = g(r, 'lsu_client_if_0_req_data')
        # lsu_req_data_t: {rw[1], mask[2], byteen[2][4], addr[2][30], attr[2][12], data[2][32], tag[62]}
        rw = bits(d, 220, 1); mask = bits(d, 218, 2); byteen = bits(d, 210, 8); tag = bits(d, 0, 62)
        if tag & 1: req_fence += 1
        elif rw: req_wr += 1
        else: req_rd += 1
        byteen_hist[(rw, byteen)] = byteen_hist.get((rw, byteen), 0) + 1
        mask_hist[mask] = mask_hist.get(mask, 0) + 1
    sv = g(r, 'lsu_client_if_0_rsp_valid'); sr = g(r, 'lsu_client_if_0_rsp_ready')
    if sv == 1 and sr == 1: rsp += 1
    if sv == 1 and sr == 0: rsp_stall += 1
    if g(r, 'branch_ctl_if_0_valid') == 1:
        br += 1
        if g(r, 'branch_ctl_if_0_taken') == 1: br_taken += 1
        if g(r, 'branch_ctl_if_0_is_trap') == 1: br_trap += 1
        if g(r, 'branch_ctl_if_0_is_mret') == 1: br_mret += 1
    if g(r, 'sched_csr_if_csr_wr_valid') == 1: csr_wr += 1
    if g(r, 'sched_csr_if_trap_csr_wr_valid') == 1:
        trap_wr += 1
        a = g(r, 'sched_csr_if_trap_csr_wr_addr'); trap_addrs[a] = trap_addrs.get(a, 0) + 1
    for k in wctl:
        if g(r, 'warp_ctl_if_%s_valid' % k) == 1:
            wctl[k] += 1
            if k == 'bar': bar_cycles.append(c)
            if k == 'wsync': wsync_cycles.append(c)
            if k == 'split' and bits(g(r, 'warp_ctl_if_split'), 34, 1): split_dvg += 1
    if g(r, 'dcr_csr_if_valid') == 1 and g(r, 'dcr_csr_if_ready') == 1: dcr_reads += 1
    if g(r, 'warp_ctl_if_lsu_sched_drained') == 0: drained_low.append(c)
    if bits(g(r, 'warp_ctl_if_warp_pending_alm_empty'), 1, 1) == 0: alm_low.append(c)

print("cycles recorded: %d (reset released at cycle index %s)" % (n, reset_release))
print("dispatch fires alu/lsu/sfu: %d/%d/%d  (valid&!ready stall cycles: %d/%d/%d)" % (*disp, *disp_stall))
print("commits alu/lsu/sfu: %d/%d/%d  (valid&!ready backpressure cycles: %d/%d/%d)" % (*commit, *commit_bp))
print("lsu requests: %d loads, %d stores, %d fences; req valid&!ready cycles: %d" % (req_rd, req_wr, req_fence, req_stall))
print("  lane masks: %s" % ', '.join('%s x%d' % (format(m, '02b'), k) for m, k in sorted(mask_hist.items())))
print("  byteen (rw, lane1|lane0): %s" % ', '.join('%s:%s x%d' % ('W' if rw else 'R', format(b, '08b'), k) for (rw, b), k in sorted(byteen_hist.items())))
print("lsu responses accepted: %d; rsp valid&!ready cycles: %d" % (rsp, rsp_stall))
print("branch resolutions: %d (taken %d, is_trap %d, is_mret %d)" % (br, br_taken, br_trap, br_mret))
print("csr writes: mscratch csr_wr_valid %d, trap_csr_wr_valid %d (addrs %s)" % (csr_wr, trap_wr, ', '.join('0x%03x x%d' % (a, k) for a, k in sorted(trap_addrs.items()))))
print("warp-ctl events: %s (split divergent: %d)" % (', '.join('%s %d' % kv for kv in wctl.items()), split_dvg))
print("dcr_csr reads (valid&ready): %d" % dcr_reads)
def rng(l):
    return "[%d..%d]" % (l[0], l[-1]) if l else "none"
print("lsu_sched_drained low %s -> bar_valid at cycles %s" % (rng(drained_low), bar_cycles))
print("warp_pending_alm_empty[1] low %s -> wsync_valid at cycles %s" % (rng(alm_low), wsync_cycles))
