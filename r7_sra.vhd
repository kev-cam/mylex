-- Item 7 (found by the ALU census after items 1-5): l3d_sra, the arithmetic
-- shift right — VX_alu_int's shr lane
--   sv2v_cast_32_signed(resize(l3d_sra(resize(shr_in1, 33), l3d_shcount(imm(4 downto 0))), 32))
-- (alu.vhd:2288, the text path's `$signed(shr_in1) >>> imm`).  No lowering
-- existed: `fcall:L3D_SRA d0 np2`.  The 33-bit result is also wider than
-- its 32-bit target — the builder now fits it (low bits), as read_verilog
-- would.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r7_sra is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of r7_sra : entity is "r7_sra.v:1";
end entity;

architecture from_verilog of r7_sra is
  signal tmp_ivl_2 : logic3d := L3D_X;
  signal tmp_ivl_3 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal shr_in1 : logic3d_vector(32 downto 0) := (others => L3D_X);
  signal y_c : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);

  impure function sv2v_cast_32_signed (
    inp : logic3d_vector(31 downto 0)
  )
  return logic3d_vector;

  impure function sv2v_cast_32_signed (
    inp : logic3d_vector(31 downto 0)
  )
  return logic3d_vector is
    variable sv2v_cast_32_signed_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_32_signed_Result := inp;
    return sv2v_cast_32_signed_Result;
  end function;
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_0: process (a, b, op) is
  begin
    tmp_ivl_2 := l3d_and(op(0), a(31));
    tmp_ivl_3 := a;
    shr_in1 := tmp_ivl_2 & tmp_ivl_3;
    y_c := sv2v_cast_32_signed(resize(l3d_sra(resize(shr_in1, 33), l3d_shcount(b(0 + 4 downto 0))), 32));
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
