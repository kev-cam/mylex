-- Item 1: the 8-entry cap on inlinable function bodies.
-- tgt-vhdl emits every package function and every sv2v_cast_<N> helper the
-- module uses as its own straight-line `impure function` body (alu_top
-- carries 21, exec_top 30).  Nine such bodies here: the HEAD walker admits
-- eight and declines the module on the ninth (`function SV2V_CAST_32 cap8`).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r1_fcap is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r1_fcap is
  signal y_c : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);

  impure function sv2v_cast_4_n0 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n1 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n2 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n3 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n4 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n5 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n6 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n7 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_4_n0 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n0_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n0_Result := inp;
    return sv2v_cast_4_n0_Result;
  end function;

  impure function sv2v_cast_4_n1 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n1_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n1_Result := inp;
    return sv2v_cast_4_n1_Result;
  end function;

  impure function sv2v_cast_4_n2 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n2_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n2_Result := inp;
    return sv2v_cast_4_n2_Result;
  end function;

  impure function sv2v_cast_4_n3 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n3_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n3_Result := inp;
    return sv2v_cast_4_n3_Result;
  end function;

  impure function sv2v_cast_4_n4 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n4_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n4_Result := inp;
    return sv2v_cast_4_n4_Result;
  end function;

  impure function sv2v_cast_4_n5 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n5_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n5_Result := inp;
    return sv2v_cast_4_n5_Result;
  end function;

  impure function sv2v_cast_4_n6 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n6_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n6_Result := inp;
    return sv2v_cast_4_n6_Result;
  end function;

  impure function sv2v_cast_4_n7 (
    inp : logic3d_vector(3 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_4_n7_Result : logic3d_vector(3 downto 0);
  begin
    sv2v_cast_4_n7_Result := inp;
    return sv2v_cast_4_n7_Result;
  end function;

  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_32_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_32_Result := inp;
    return sv2v_cast_32_Result;
  end function;
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_0: process (a, b) is
  begin
    y_c := sv2v_cast_32(sv2v_cast_4_n7(l3d_xor(a(28 + 3 downto 28), b(0 + 3 downto 0))) & sv2v_cast_4_n6(a(24 + 3 downto 24)) & sv2v_cast_4_n5(a(20 + 3 downto 20)) & sv2v_cast_4_n4(a(16 + 3 downto 16)) & sv2v_cast_4_n3(a(12 + 3 downto 12)) & sv2v_cast_4_n2(a(8 + 3 downto 8)) & sv2v_cast_4_n1(a(4 + 3 downto 4)) & sv2v_cast_4_n0(a(0 + 3 downto 0)));
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
