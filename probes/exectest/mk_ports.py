#!/usr/bin/env python3
"""Derive the flat port list (dir width name) of exec_top from the sv2v
output, where every width is numeric:  python3 mk_ports.py exec.v > ports.txt
The wrapper declares its widths symbolically ($bits(dispatch_t), NW_WIDTH...);
the testbench generator needs the resolved numbers, and taking them from the
same exec.v that is translated keeps both sides of the differential test on
one definition.  sv2v writes a non-ANSI header (`module exec_top (a, b, ...);`
followed by `input wire [w-1:0] a;` declarations), which is what is parsed."""
import re, sys

src = open(sys.argv[1]).read()
m = re.search(r'\bmodule\s+exec_top\s*\((.*?)\);(.*?)\bendmodule\b', src, re.S)
if not m:
    raise SystemExit('module exec_top not found in ' + sys.argv[1])
names = [n.strip() for n in m.group(1).split(',') if n.strip()]
body = m.group(2)
for name in names:
    r = re.search(r'^\s*(input|output)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s*)?%s\s*;' % re.escape(name),
                  body, re.M)
    if not r:
        raise SystemExit('no declaration for port ' + name)
    kind, msb, lsb = r.groups()
    w = 1 if msb is None else abs(int(msb) - int(lsb)) + 1
    print('%-6s %4d  %s' % (kind, w, name))
