#!/usr/bin/env python3
"""Generate the port-list-derived parts of the exec_top differential test.

Reads ports_<tier>.txt (dir width name, one wrapper port per line) and emits
  tb_exec.sv          from tb_exec.sv.in  (fills //@@PORTMAP@@ and //@@RECORD@@)
  tb_exec_replay.vhd  the NVC replay/compare bench
so the vector field order (all inputs, then all outputs) is identical on both
sides by construction.  Inputs are recorded as nibble-padded hex (%h: they
never contain x); outputs are recorded bit-exact (%b, one character per bit)
so an x bit never hides its defined neighbours -- vvp's %h prints a whole
nibble as 'X' when any of its bits is x.

    python3 gen_tb.py [--tier tierA|tierB] [--ports FILE] [--outdir DIR]

Tier A (default: ports_tierA.txt, files written next to this script) has
three dispatch/commit ports; Tier B (F enabled) has a fourth (EX_FPU).  The
number of commit ports is taken from the port list, so the same template
serves both; the template's FPU stream is under `ifndef VX_CFG_EXT_F_DISABLE.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--tier', default='tierA', choices=['tierA', 'tierB'])
ap.add_argument('--ports', default=None, help='port list (default ports_<tier>.txt)')
ap.add_argument('--outdir', default=HERE, help='where tb_exec.sv / tb_exec_replay.vhd are written')
args = ap.parse_args()
TIER = args.tier
PORTS = args.ports or os.path.join(HERE, 'ports_%s.txt' % TIER)   # exported probe layout
if not os.path.exists(PORTS):
    PORTS = os.path.join(HERE, '..', 'ports_%s.txt' % TIER)        # scratchpad layout
OUTDIR = args.outdir

ports = []
for line in open(PORTS):
    f = line.split()
    if len(f) != 3:
        continue
    d, w, n = f[0], int(f[1]), f[2]
    if n == 'clk':
        continue                      # clk is generated on both sides
    ports.append((d, w, n))

ins  = [p for p in ports if p[0] == 'input']
outs = [p for p in ports if p[0] == 'output']
fields = ins + outs                   # vector order: inputs then outputs
assert ins[0][2] == 'reset', "reset must be the first recorded input"

# handshake outputs: their expectation must be defined once reset is released,
# otherwise the X-as-don't-care compare would be vacuous
hs_outs = [p for p in outs if p[2].endswith('_valid') or p[2].endswith('_ready')]

# commit ports (EX_ALU, EX_LSU, EX_SFU[, EX_FPU]) for the DUT-side tallies
n_commit_ports = len([p for p in outs if p[2].startswith('commit_if_') and p[2].endswith('_valid')])
unit_names = ['alu', 'lsu', 'sfu', 'fpu'][:n_commit_ports]
assert n_commit_ports == (4 if TIER == 'tierB' else 3), \
    "%s: %d commit ports in %s" % (TIER, n_commit_ports, PORTS)

def padw(w):
    return (w + 3) // 4 * 4

# ---------------------------------------------------------------- SV side
portmap = ',\n'.join('        .%s(%s)' % (n, n) for (_, _, n) in [('input', 1, 'clk')] + ports)

fmt = ' '.join(['%h'] * len(ins) + ['%b'] * len(outs))
args = []
for (d, w, n) in fields:
    p = padw(w) - w
    args.append("{%d'b0, %s}" % (p, n) if p else n)
record = '        $fwrite(fd, "%s\\n",\n            %s);' % (fmt, ',\n            '.join(args))

tmpl = open(os.path.join(HERE, 'tb_exec.sv.in')).read()
assert '//@@PORTMAP@@' in tmpl and '//@@RECORD@@' in tmpl
sv = tmpl.replace('//@@PORTMAP@@', portmap).replace('//@@RECORD@@', record)
open(os.path.join(OUTDIR, 'tb_exec.sv'), 'w').write(sv)

# -------------------------------------------------------------- VHDL side
def sigdecl(d, w, n):
    if w == 1:
        # reset starts asserted, exactly as the oracle's `reg reset = 1`
        init = ' := L3D_1' if n == 'reset' else (' := L3D_0' if d == 'input' else '')
        return '    signal %s : logic3d%s;' % (n, init)
    init = ' := (others => L3D_0)' if d == 'input' else ''
    return '    signal %s : logic3d_vector(%d downto 0)%s;' % (n, w - 1, init)

def drive_lines(lv, indent):
    """Read this line's input fields from line variable `lv` and drive the DUT."""
    out = []
    for (d, w, n) in ins:
        if w == 1:
            out.append('%srdhex(%s, v_%s); %s <= to_logic3d(v_%s(0));' % (indent, lv, n, n, n))
        else:
            out.append('%srdhex(%s, v_%s); %s <= slv2l3d(v_%s(%d downto 0));' % (indent, lv, n, n, n, w - 1))
    return out

v = []
v.append('''-- NVC replay bench for exec_top (VX_execute, %s): re-applies every
-- cycle's recorded inputs from vectors.txt (written by the vvp oracle
-- tb_exec.sv) at the falling clock edge and compares every output 1 ns
-- later, from cycle 0.  An 'X' in an expected bit is a don't-care; the
-- handshake expectations (every *_valid / *_ready output) are required to be
-- defined once reset is released so the compare cannot be vacuous.
-- Pre-history matches the oracle exactly: reset starts asserted, row 0's
-- inputs are driven from time 0 (the oracle's initial values), the first
-- rising edge is at 5 ns and row k is sampled by the edge at 5 + 10k ns.
-- GENERATED by gen_tb.py from %s -- do not edit by hand.
library ieee;''' % ('Tier A' if TIER == 'tierA' else 'Tier B', os.path.basename(PORTS)))
v.append('''use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_exec_replay is end entity;

architecture t of tb_exec_replay is
    signal clk : logic3d := L3D_0;
    signal running : boolean := true;
''')
for p in ports:
    v.append(sigdecl(*p))
v.append('''
    -- expected bit 'X' (vvp printed x) is a don't-care
    function matches(act, exp : std_logic_vector) return boolean is
        alias a : std_logic_vector(act'length-1 downto 0) is act;
        alias e : std_logic_vector(exp'length-1 downto 0) is exp;
    begin
        for i in a'range loop
            if e(i) /= 'X' and e(i) /= 'U' and a(i) /= e(i) then return false; end if;
        end loop;
        return true;
    end function;

    -- lossless std_logic_vector -> logic3d_vector (keeps X/Z)
    function slv2l3d(s : std_logic_vector) return logic3d_vector is
        alias a : std_logic_vector(s'length-1 downto 0) is s;
        variable r : logic3d_vector(s'length-1 downto 0);
    begin
        for i in a'range loop r(i) := to_logic3d(a(i)); end loop;
        return r;
    end function;

    -- read one nibble-padded hex token as vvp's %h prints it: 0-9 a-f A-F,
    -- and x/X (all- or part-unknown nibble) / z/Z, which IEEE HREAD rejects
    -- (and then leaves the line pointer mid-token).
    -- v'length/4 characters are consumed after skipping blanks.
    procedure rdhex(l : inout line; v : out std_logic_vector) is
        alias a : std_logic_vector(v'length-1 downto 0) is v;
        variable c : character;
        variable ok : boolean;
        variable nib : std_logic_vector(3 downto 0);
    begin
        loop
            read(l, c, ok);
            assert ok report "vectors.txt: short line" severity failure;
            exit when c /= ' ' and c /= HT;
        end loop;
        for i in v'length/4 - 1 downto 0 loop
            case c is
                when '0' => nib := x"0"; when '1' => nib := x"1"; when '2' => nib := x"2"; when '3' => nib := x"3";
                when '4' => nib := x"4"; when '5' => nib := x"5"; when '6' => nib := x"6"; when '7' => nib := x"7";
                when '8' => nib := x"8"; when '9' => nib := x"9";
                when 'a' | 'A' => nib := x"A"; when 'b' | 'B' => nib := x"B"; when 'c' | 'C' => nib := x"C";
                when 'd' | 'D' => nib := x"D"; when 'e' | 'E' => nib := x"E"; when 'f' | 'F' => nib := x"F";
                when 'x' | 'X' => nib := "XXXX";
                when 'z' | 'Z' => nib := "ZZZZ";
                when others => assert false report "vectors.txt: bad hex char '" & c & "'" severity failure;
            end case;
            a(i*4+3 downto i*4) := nib;
            if i > 0 then
                read(l, c, ok);
                assert ok report "vectors.txt: short token" severity failure;
            end if;
        end loop;
    end procedure;

    -- read one binary token as vvp's %b prints it: exactly one character
    -- per bit (0/1/x/z), so an x bit is a don't-care for that bit only.
    procedure rdbin(l : inout line; v : out std_logic_vector) is
        alias a : std_logic_vector(v'length-1 downto 0) is v;
        variable c : character;
        variable ok : boolean;
    begin
        loop
            read(l, c, ok);
            assert ok report "vectors.txt: short line" severity failure;
            exit when c /= ' ' and c /= HT;
        end loop;
        for i in v'length - 1 downto 0 loop
            case c is
                when '0' => a(i) := '0'; when '1' => a(i) := '1';
                when 'x' | 'X' => a(i) := 'X'; when 'z' | 'Z' => a(i) := 'Z';
                when others => assert false report "vectors.txt: bad bin char '" & c & "'" severity failure;
            end case;
            if i > 0 then
                read(l, c, ok);
                assert ok report "vectors.txt: short token" severity failure;
            end if;
        end loop;
    end procedure;
begin
    dut: entity work.exec_top
        port map (
            clk => clk,''')
v.append(',\n'.join('            %s => %s' % (n, n) for (_, _, n) in ports))
v.append('''        );

    -- same phase as the oracle's `reg clk = 0; always #5 clk = ~clk`:
    -- rising edges at 5 + 10k ns, falling edges at 10 + 10k ns
    clkgen: process begin
        wait for 5 ns;
        while running loop
            clk <= L3D_1; wait for 5 ns;
            clk <= L3D_0; wait for 5 ns;
        end loop;
        wait;
    end process;

    replay: process
        file f : text open read_mode is "vectors.txt";
        variable l, l0 : line;
        variable first : boolean;''')
for (d, w, n) in fields:
    v.append('        variable v_%s : std_logic_vector(%d downto 0);' % (n, padw(w) - 1))
v.append('''        variable cyc, bad, shown : integer := 0;
        variable %s, n_lsu_req, n_lsu_rsp, n_br : integer := 0;
        variable n_csr_wr, n_trap_wr, n_wctl : integer := 0;''' % ', '.join('n_commit%d' % u for u in range(n_commit_ports)))
v.append('''        procedure chk(name : string; act, exp : std_logic_vector) is
        begin
            if not matches(act, exp) then
                bad := bad + 1;
                if shown < 40 then
                    shown := shown + 1;
                    report "cycle " & integer'image(cyc) & ": " & name & " mismatch act="
                        & to_hstring(act) & " exp=" & to_hstring(exp) severity warning;
                end if;
            end if;
        end procedure;
        procedure defined(name : string; e : std_logic_vector) is
        begin
            for i in e'range loop
                assert e(i) = '0' or e(i) = '1'
                    report "cycle " & integer'image(cyc) & ": expected " & name
                         & " is undefined after reset -- the compare would be vacuous"
                    severity failure;
            end loop;
        end procedure;
    begin
        -- Pre-history: the oracle's DUT sees its first rising edge (5 ns) with
        -- reset = 1 and the testbench's initial input values, which are what
        -- row 0 records.  Drive row 0 from time 0 (a copy of the line; the
        -- line itself is consumed again at the first falling edge).
        readline(f, l);
        l0 := new string'(l.all);''')
v.extend(drive_lines('l0', '        '))
v.append('''        deallocate(l0);
        first := true;
        while first or not endfile(f) loop
            if not first then readline(f, l); end if;
            first := false;
            -- mirror the oracle recorder: inputs applied AT the falling edge,
            -- outputs compared 1 ns later (they reflect the preceding rising edge)
            wait until clk = L3D_0;''')
v.extend(drive_lines('l', '            '))
for (d, w, n) in outs:
    v.append('            rdbin(l, v_%s);' % n)
v.append('''            wait for 1 ns;
            -- handshake expectations must be defined once reset is released''')
v.append('            if v_reset(0) = \'0\' then')
for (d, w, n) in hs_outs:
    v.append('                defined("%s", v_%s(%d downto 0));' % (n, n, w - 1))
v.append('            end if;')
for (d, w, n) in outs:
    v.append('            chk("%s", to_std_logic_vector(%s), v_%s(%d downto 0));' % (n, n, n, w - 1))
v.append('''            -- coverage tallies from the NVC DUT's own outputs (a handshake
            -- seen here is consumed by the next rising edge; the ready inputs
            -- are this bench's, driven from the vector at the falling edge)''')
for u in range(n_commit_ports):
    v.append('            if commit_if_%d_valid = L3D_1 and commit_if_%d_ready = L3D_1 then n_commit%d := n_commit%d + 1; end if;' % (u, u, u, u))
v.append('''            if lsu_client_if_0_req_valid = L3D_1 and lsu_client_if_0_req_ready = L3D_1 then n_lsu_req := n_lsu_req + 1; end if;
            if lsu_client_if_0_rsp_valid = L3D_1 and lsu_client_if_0_rsp_ready = L3D_1 then n_lsu_rsp := n_lsu_rsp + 1; end if;
            if branch_ctl_if_0_valid = L3D_1 then n_br := n_br + 1; end if;
            if sched_csr_if_csr_wr_valid = L3D_1 then n_csr_wr := n_csr_wr + 1; end if;
            if sched_csr_if_trap_csr_wr_valid = L3D_1 then n_trap_wr := n_trap_wr + 1; end if;
            if warp_ctl_if_wspawn_valid = L3D_1 or warp_ctl_if_tmc_valid = L3D_1 or warp_ctl_if_split_valid = L3D_1
               or warp_ctl_if_sjoin_valid = L3D_1 or warp_ctl_if_bar_valid = L3D_1 or warp_ctl_if_wsync_valid = L3D_1 then
                n_wctl := n_wctl + 1;
            end if;
            cyc := cyc + 1;
        end loop;
        running <= false;
        if bad = 0 then
            report "PASS: " & integer'image(cyc) & " cycles replayed and compared from cycle 0 (outputs bit-exact, x = don't-care); "
                 & "DUT commits %s="
                 & %s
                 & ", lsu req/rsp=" & integer'image(n_lsu_req) & "/" & integer'image(n_lsu_rsp)''' % (
    '/'.join(unit_names),
    ' & "/" & '.join('integer\'image(n_commit%d)' % u for u in range(n_commit_ports))))
v.append('''                 & ", branches=" & integer'image(n_br) & ", csr_wr=" & integer'image(n_csr_wr)
                 & ", trap_csr_wr=" & integer'image(n_trap_wr) & ", warp_ctl=" & integer'image(n_wctl)
                 & " -- all outputs identical to the vvp oracle every cycle";
        else
            report "FAIL: " & integer'image(bad) & " output mismatches over " & integer'image(cyc) & " cycles" severity failure;
        end if;
        wait;
    end process;
end architecture;
''')
open(os.path.join(OUTDIR, 'tb_exec_replay.vhd'), 'w').write('\n'.join(v))
print("generated tb_exec.sv (%d ports, %d vector fields: %d hex inputs + %d binary outputs, %d handshake guards) and tb_exec_replay.vhd (%s, %d commit ports) in %s"
      % (len(ports), len(fields), len(ins), len(outs), len(hs_outs), TIER, n_commit_ports, OUTDIR))
