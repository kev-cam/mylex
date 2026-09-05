#!/usr/bin/env python3
# r30_<v>: VX_fcvt_unit's stage-0 exponent process, verbatim (A) and with one
# construct removed per variant -- bisecting the r29_exp mismatch.
import re
W = "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/walker"
fcvt = open(f"{W}/fcvt.vhd").read()

def func(name):
    m = list(re.finditer(rf"  (?:impure )?function {re.escape(name)} ?\(.*?end function;\n", fcvt, re.S))
    assert m, name
    return m[-1].group(0)
FUNCS = "".join(func(n) for n in ["sv2v_cast_36466", "sv2v_cast_36466_signed", "sv2v_cast_99F89"])

L12 = "logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1)"   # 31
BIAS = "logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1)"  # 127

EXPR = {
 "A": "(sv2v_cast_36466(resize(src_exp_raw, 12)) - src_bias_s) + sv2v_cast_36466(resize((L3D_0 & fclass(4)), 12))",
 "C": "(sv2v_cast_36466(resize(src_exp_raw, 12)) - src_bias_s)",
 "D": "(resize(src_exp_raw, 12) - src_bias_s) + resize((L3D_0 & fclass(4)), 12)",
 "E": "sv2v_cast_36466(resize(src_exp_raw, 12))",
 "F": "resize(src_exp_raw, 12) - src_bias_s",
 "G": "sv2v_cast_36466(resize((L3D_0 & fclass(4)), 12))",
}
# B = A with src_bias_s driven from a port (not a constant-driven signal)
BIASDRV = {k: f"  src_bias_s <= {BIAS};" for k in EXPR}
EXPR["B"] = EXPR["A"]
BIASDRV["B"] = "  src_bias_s <= L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_0 & L3D_1 & L3D_1 & L3D_1 & L3D_1 & L3D_1 & L3D_1 & b(0);"

for v, expr in EXPR.items():
    name = f"r30_{v}"
    s = f"""-- VX_fcvt_unit stage 0 (exec.vhd:72140, the `always` at exec.v:6108): the
-- exponent unpack.  r29 showed unpacked_exp_s0 wrong with all its inputs
-- right.  Variant {v}: v_unpacked_exp_s0 := {expr}
library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
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
{FUNCS}
  signal sig_sv2v_0 : logic3d := L3D_X;
  signal is_itof : logic3d := L3D_X;
  signal i_mag : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal fp_unpacked_mant : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal src_exp_raw : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal src_bias_s : logic3d_vector(11 downto 0) := (others => L3D_X);
  signal fclass : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal unpacked_exp_s0 : logic3d_vector(11 downto 0) := (others => L3D_X);
  signal unpacked_mant_s0 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  sig_sv2v_0 <= op(3);
  is_itof <= op(0);
  i_mag <= b;
  fp_unpacked_mant <= a;
  src_exp_raw <= a(7 downto 0);
{BIASDRV[v]}
  fclass <= b(6 downto 0);
  process (sig_sv2v_0, is_itof, i_mag, fp_unpacked_mant, src_exp_raw, src_bias_s, fclass) is
    variable v_unpacked_exp_s0 : logic3d_vector(11 downto 0);
    variable v_unpacked_mant_s0 : logic3d_vector(31 downto 0);
  begin
    v_unpacked_mant_s0 := unpacked_mant_s0;
    v_unpacked_exp_s0 := unpacked_exp_s0;
    if is_one(sig_sv2v_0) then
    end if;
    if is_one(is_itof) then
      v_unpacked_mant_s0 := sv2v_cast_99F89(i_mag);
      v_unpacked_exp_s0 := sv2v_cast_36466_signed({L12});
    else
      v_unpacked_mant_s0 := fp_unpacked_mant;
      v_unpacked_exp_s0 := {expr};
    end if;
    unpacked_exp_s0 <= v_unpacked_exp_s0;
    unpacked_mant_s0 <= v_unpacked_mant_s0;
  end process;
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        yr <= (others => L3D_0);
      else
        yr <= (unpacked_exp_s0 & unpacked_mant_s0(19 downto 0)) xor (a(31 downto 12) & b(11 downto 0));
      end if;
    end if;
    wait on clk;
  end process;
end architecture;
"""
    open(f"{name}.vhd", "w").write(s)
print("wrote r30_" + " r30_".join(EXPR))
