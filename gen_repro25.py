#!/usr/bin/env python3
# r25/r26/r27: VX_lzc, VX_fp_rounding, VX_fp_classifier standalone (verbatim
# from the translated Tier B design) -- bisecting the r24_fcvt mismatch.
import re
exec(open("gen_repro24.py").read().split("need, done, out =")[0])   # block(), txt

HDR = """library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;
entity {name} is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of {name} is
"""

def closure(root):
    need, done, out = [root], [], []
    while need:
        n = need.pop(0)
        if n.lower() in [d.lower() for d in done]:
            continue
        b = block(n); done.append(n); out.append(b)
        for dep in re.findall(r"entity work\.(\w+)", b):
            if dep.lower() not in [d.lower() for d in done]:
                need.append(dep)
    return "".join(reversed(out))

lzc = closure("VX_lzc") + HDR.format(name="r25_lzc") + """  signal data_out : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal valid_out : logic3d := L3D_X;
  signal yc : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  u : entity work.VX_lzc port map (data_in => a, data_out => data_out, valid_out => valid_out);
  yc <= (b(26 downto 0) & data_out) xor (a(31 downto 1) & valid_out);
  process is begin
    if rising_edge(clk) then yr <= yc; end if;
    wait on clk;
  end process;
  y <= yr;
end architecture;
"""
rnd = closure("VX_fp_rounding") + HDR.format(name="r26_round") + """  signal abs_rounded_o : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal sign_o : logic3d := L3D_X;
  signal yc : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  u : entity work.VX_fp_rounding
    port map (abs_value_i => a, sign_i => b(0), round_sticky_bits_i => b(2 downto 1),
              rnd_mode_i => op(2 downto 0), effective_subtraction_i => b(3),
              abs_rounded_o => abs_rounded_o, sign_o => sign_o);
  yc <= abs_rounded_o xor (b(31 downto 1) & sign_o);
  process is begin
    if rising_edge(clk) then yr <= yc; end if;
    wait on clk;
  end process;
  y <= yr;
end architecture;
"""
cls = closure("VX_fp_classifier") + HDR.format(name="r27_class") + """  signal clss_o : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal yc : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  u : entity work.VX_fp_classifier port map (exp_i => a(30 downto 23), man_i => a(22 downto 0), clss_o => clss_o);
  yc <= (b(24 downto 0) & clss_o) xor a;
  process is begin
    if rising_edge(clk) then yr <= yc; end if;
    wait on clk;
  end process;
  y <= yr;
end architecture;
"""
open("r25_lzc.vhd", "w").write(lzc)
open("r26_round.vhd", "w").write(rnd)
open("r27_class.vhd", "w").write(cls)
print("wrote r25_lzc.vhd r26_round.vhd r27_class.vhd")
