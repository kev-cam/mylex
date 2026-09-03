"""Decode the events of the oracle's vector file (commits, branches, CSR and
warp-control events, DCR reads) one line per cycle.  Field order and radix as
in gen_tb.py: inputs nibble-padded hex, outputs binary.

    python3 decode_commits.py [--tier tierA|tierB] [vectors file]

commit_t: {eop, sop, data[2][32], bytesel[4], rd[NUM_REGS_BITS], wr_xregs[2], wb,
PC[30], tmask[2], sid, cta, wid, uuid}; NUM_REGS_BITS is 5 in Tier A and 6 in
Tier B (F enabled), so every field above rd moves up one bit there.  FPU
operands/results with the IEEE reference check: decode_tierB.py."""
import argparse, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--tier', default='tierA', choices=['tierA', 'tierB'])
ap.add_argument('vec', nargs='?', default=None)
a = ap.parse_args()
PORTS = os.path.join(HERE, 'ports_%s.txt' % a.tier)
if not os.path.exists(PORTS):
    PORTS = os.path.join(HERE, '..', 'ports_%s.txt' % a.tier)
VEC = a.vec or os.path.join(HERE, 'vectors.txt' if a.tier == 'tierA' else 'vectors_tierB.txt')
RDW = 5 if a.tier == 'tierA' else 6           # NUM_REGS_BITS
names = ['ALU', 'LSU', 'SFU', 'FPU'][:3 if a.tier == 'tierA' else 4]
ports = [(f[0], int(f[1]), f[2]) for f in (l.split() for l in open(PORTS)) if len(f) == 3 and f[2] != 'clk']
fields = [p for p in ports if p[0] == 'input'] + [p for p in ports if p[0] == 'output']
idx = {n: i for i, (_, _, n) in enumerate(fields)}
base = [16 if d == 'input' else 2 for (d, _, _) in fields]
def val(t, b): return None if ('x' in t.lower() or 'z' in t.lower()) else int(t, b)
def bits(v, lo, w): return (v >> lo) & ((1 << w) - 1)
def hx(v): return ("%x" % v) if v is not None else "x"
RD, WB, PC, TM, WID = 70, 70 + RDW + 2, 70 + RDW + 3, 70 + RDW + 33, 70 + RDW + 37
for c, line in enumerate(open(VEC)):
    r = [val(t, b) for t, b in zip(line.split(), base)]
    for u in range(len(names)):
        if r[idx['commit_if_%d_valid' % u]] == 1 and r[idx['commit_if_%d_ready' % u]] == 1:
            d = r[idx['commit_if_%d_data' % u]]
            if d is None:
                print("%3d %s PC=?? (data has x)" % (c, names[u])); continue
            print("%3d %s wid=%d tmask=%s PC=%03x wb=%d rd=%2d d1=%08x d0=%08x" % (c, names[u], bits(d,WID,1), format(bits(d,TM,2),'02b'), bits(d,PC,30), bits(d,WB,1), bits(d,RD,RDW), bits(d,34,32), bits(d,2,32)))
    if r[idx['branch_ctl_if_0_valid']] == 1:
        print("%3d BR  wid=%d taken=%d dest=%08x trap=%d mret=%d cause=%d" % (c, r[idx['branch_ctl_if_0_wid']], r[idx['branch_ctl_if_0_taken']], r[idx['branch_ctl_if_0_dest']] << 2, r[idx['branch_ctl_if_0_is_trap']], r[idx['branch_ctl_if_0_is_mret']], r[idx['branch_ctl_if_0_trap_cause']]))
    if r[idx['sched_csr_if_csr_wr_valid']] == 1:
        print("%3d CSRWR mscratch wid=%d data=%08x" % (c, r[idx['sched_csr_if_csr_wr_wid']], r[idx['sched_csr_if_csr_wr_data']]))
    if r[idx['sched_csr_if_trap_csr_wr_valid']] == 1:
        print("%3d TRAPWR addr=%03x wid=%d data=%08x" % (c, r[idx['sched_csr_if_trap_csr_wr_addr']], r[idx['sched_csr_if_csr_wr_wid']], r[idx['sched_csr_if_trap_csr_wr_data']]))
    for k in ['wspawn', 'tmc', 'split', 'sjoin', 'bar', 'wsync']:
        if r[idx['warp_ctl_if_%s_valid' % k]] == 1:
            pl = r[idx["warp_ctl_if_%s" % k]] if k != "wsync" else 0
            print("%3d WCTL %s wid=%s payload=%s bar_addr=%s" % (c, k, hx(r[idx["warp_ctl_if_wid"]]), hx(pl), hx(r[idx["warp_ctl_if_bar_addr"]])))
    if r[idx['dcr_csr_if_valid']] == 1 and r[idx['dcr_csr_if_ready']] == 1:
        print("%3d DCR addr=%03x value=%08x" % (c, r[idx['dcr_csr_if_addr']], r[idx['dcr_csr_if_value']]))
