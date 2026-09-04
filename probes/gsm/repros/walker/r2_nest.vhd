-- Item 2: a function call INSIDE an inlined function body (inline depth 1).
-- The package bodies call the sv2v casts: VX_gpu_pkg_to_fullPC(pc) =
-- sv2v_cast_32(pc & "00"), VX_gpu_pkg_from_fullPC(pc) = sv2v_cast_30(resize(
-- pc srl 2, 30)).  HEAD inlines only at depth 0 and declines the call:
-- `fcall:SV2V_CAST_32 d1 np1@seq-assign`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r2_nest is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r2_nest is
  signal tmp_ivl_1 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_2 : logic3d_vector(29 downto 0) := (others => L3D_X);
  signal y_c : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);

  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_30 (
    inp : logic3d_vector(29 downto 0)
  )
  return logic3d_vector;

  impure function VX_gpu_pkg_to_fullPC (
    pc : logic3d_vector(29 downto 0)
  )
  return logic3d_vector;

  impure function VX_gpu_pkg_from_fullPC (
    pc : logic3d_vector(31 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_32_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_32_Result := inp;
    return sv2v_cast_32_Result;
  end function;

  impure function sv2v_cast_30 (
    inp : logic3d_vector(29 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_30_Result : logic3d_vector(29 downto 0);
  begin
    sv2v_cast_30_Result := inp;
    return sv2v_cast_30_Result;
  end function;

  -- Generated from function VX_gpu_pkg_to_fullPC
  impure function VX_gpu_pkg_to_fullPC (
    pc : logic3d_vector(29 downto 0)
  )
  return logic3d_vector is
    variable VX_gpu_pkg_to_fullPC_Result : logic3d_vector(31 downto 0);
  begin
    VX_gpu_pkg_to_fullPC_Result := sv2v_cast_32(pc & logic3d_vector'(L3D_0, L3D_0));
    return VX_gpu_pkg_to_fullPC_Result;
  end function;

  -- Generated from function VX_gpu_pkg_from_fullPC
  impure function VX_gpu_pkg_from_fullPC (
    pc : logic3d_vector(31 downto 0)
  )
  return logic3d_vector is
    variable VX_gpu_pkg_from_fullPC_Result : logic3d_vector(29 downto 0);
  begin
    VX_gpu_pkg_from_fullPC_Result := sv2v_cast_30(resize(pc srl l3d_shcount(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0)), 30));
    return VX_gpu_pkg_from_fullPC_Result;
  end function;
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_0: process (a, b) is
  begin
    tmp_ivl_1 := VX_gpu_pkg_to_fullPC(a(0 + 29 downto 0));
    tmp_ivl_2 := VX_gpu_pkg_from_fullPC(b);
    y_c := l3d_xor(tmp_ivl_1, tmp_ivl_2 & logic3d_vector'(L3D_0, L3D_0));
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= y_c;
      end if;
    end if;
  end process;
end architecture;
