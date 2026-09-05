#!/usr/bin/env python3
# r24: the whole VX_fcvt_unit (with VX_fp_classifier, VX_fp_rounding,
# VX_lzc, VX_pipe_register*) lifted verbatim from the translated Tier B
# design, under a wrapper that drives float->int conversions.
import re, sys
EXEC = "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.vhd"
txt = open(EXEC).read()

def block(name):
    # from the `library ieee;` prologue before `entity <name> is` to the end
    # of its architecture
    m = re.search(rf"^entity {name} is\b", txt, re.M | re.I)
    assert m, name
    start = txt.rfind("library ieee;", 0, m.start())
    a = re.search(rf"^architecture \w+ of {name} is\b", txt[m.end():], re.M | re.I)
    assert a, name
    e = txt.find("end architecture;", m.end() + a.end())
    return txt[start:e + len("end architecture;")] + "\n"

need, done, out = ["VX_fcvt_unit"], [], []
while need:
    n = need.pop(0)
    if n.lower() in [d.lower() for d in done]:
        continue
    b = block(n)
    done.append(n)
    out.append(b)
    for dep in re.findall(r"entity work\.(\w+)", b):
        if dep.lower() not in [d.lower() for d in done]:
            need.append(dep)
print("entities:", done)

wrapper = """
library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;
-- The first real Tier B walker build with all 119 modules admitted was
-- bit-exact except the float->int results (cycles 464..528: F2I/F2U, e.g.
-- 2.5 RNE -> 10 instead of 2).  This is VX_fcvt_unit and everything under
-- it, verbatim from the translated design, converting floats with
-- exponents 128..143 (integers 2..2^16 x mantissa) under every rounding
-- mode, signed and unsigned; y = result xor fflags.
entity r24_fcvt is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r24_fcvt is
  signal dataa : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal frm : logic3d_vector(2 downto 0) := (others => L3D_X);
  signal is_signed : logic3d := L3D_X;
  signal result : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal fflags : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal one : logic3d := L3D_1;
  signal zero : logic3d := L3D_0;
begin
  dataa <= a(31) & L3D_1 & L3D_0 & L3D_0 & L3D_0 & op & a(22 downto 0);
  frm <= b(2 downto 0) when is_one(b(3)) else L3D_0 & b(1 downto 0);   -- 0..4 mostly
  is_signed <= b(4);
  u : entity work.VX_fcvt_unit
    port map (clk => clk, reset => reset, enable => one, mask => one, frm => frm,
              is_itof => zero, is_ftoi => one, is_f2f => zero, is_signed => is_signed,
              is_int64 => zero, src_fmt => zero, dst_fmt => zero,
              dataa => dataa, result => result, fflags => fflags);
  y <= result xor (fflags & b(31) & b(30) & b(29) & b(28) & b(27) & b(26) & b(25) & b(24) & b(23) & b(22) & b(21) & b(20) & b(19) & b(18) & b(17) & b(16) & b(15) & b(14) & b(13) & b(12) & b(11) & b(10) & b(9) & b(8) & b(7) & b(6) & b(5));
end architecture;
"""
open("r24_fcvt.vhd", "w").write("".join(reversed(out)) + wrapper)
print("wrote r24_fcvt.vhd")
