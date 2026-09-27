#!/usr/bin/env python3
"""Exhaustive functional + dual-rail well-formedness check of the popcount4
QDI direct-threshold netlist, reusing verify_direct.py's generic TH-cell
netlist simulator (its main() is sha_slice-specific; the Net class is not).
Scope: DATA-phase functional equivalence vs the C semantics + rail
well-formedness on every one of the 256 inputs.  (The full 4-phase hazard /
NULL-return machinery in verify_direct.py remains sha_slice-only -- reported
as a backend gap, not silently skipped.)"""
import sys
sys.path.insert(0, "/usr/local/src/stat-sim/qal/synth/threeway")
from verify_direct import load, Net

cells, ports = load(sys.argv[1] if len(sys.argv) > 1
                    else "polysynth_pc4_c/popcount4.qdi_direct_cd.v", "popcount4")
N = Net(cells, ports)
print("netlist: %d TH cells, %d input rail bits" % (len(cells), len(N.inbits)))
bad = 0
for x in range(256):
    v = N.drive(dict(x=x))
    got = N.read(v, "out")
    want = bin(x & 0xF).count("1")
    ok = got == want and N.welformed(v, "out")
    if not ok:
        bad += 1
        if bad <= 5:
            print("  MISMATCH x=%02x got=%x want=%x wf=%s"
                  % (x, got, want, N.welformed(v, "out")))
print("RESULT: %s (256/256 exhaustive, functional + rail well-formedness)"
      % ("PASS" if bad == 0 else "FAIL %d" % bad))
sys.exit(1 if bad else 0)
