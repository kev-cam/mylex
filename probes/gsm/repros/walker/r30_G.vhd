-- VX_fcvt_unit stage 0 (exec.vhd:72140, the `always` at exec.v:6108): the
-- exponent unpack.  r29 showed unpacked_exp_s0 wrong with all its inputs
-- right.  Variant G: v_unpacked_exp_s0 := sv2v_cast_36466(resize((L3D_0 & fclass(4)), 12))
library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;
entity r30_G is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r30_G is
  impure function sv2v_cast_36466 (
    inp : logic3d_vector(11 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_36466_Result : logic3d_vector(11 downto 0);
  begin
    sv2v_cast_36466_Result := inp;
    return sv2v_cast_36466_Result;
  end function;
  impure function sv2v_cast_36466_signed (
    inp : logic3d_vector(11 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_36466_signed_Result : logic3d_vector(11 downto 0);
  begin
    sv2v_cast_36466_signed_Result := inp;
    return sv2v_cast_36466_signed_Result;
  end function;
  impure function sv2v_cast_99F89 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_99F89_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_99F89_Result := inp;
    return sv2v_cast_99F89_Result;
  end function;

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
  src_bias_s <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
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
      v_unpacked_exp_s0 := sv2v_cast_36466_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1));
    else
      v_unpacked_mant_s0 := fp_unpacked_mant;
      v_unpacked_exp_s0 := sv2v_cast_36466(resize((L3D_0 & fclass(4)), 12));
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
