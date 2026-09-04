-- Item 4: a SLICE write to a process variable inside a case arm.
-- The per-lane comb processes pre-copy the whole result vector into a
-- variable, write one lane's slice per arm and commit that slice
-- (VX_alu_int g_msc_result, alu.vhd:2340-2360; two lane processes drive the
-- two halves of one 64-bit signal).  HEAD builds process variables only
-- straight-line / whole-target and declines: `var-assign k23 d1`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r4_slice_arm is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of r4_slice_arm : entity is "r4_slice_arm.v:1";
end entity;

architecture from_verilog of r4_slice_arm is
  signal msc_result : logic3d_vector(63 downto 0) := (others => L3D_X);
  signal y_c : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  -- Generated from always process in g_msc_result[0]
  process (op, a, b) is
    variable Verilog_Case_Ex : unsigned(1 downto 0);
    variable v_msc_result : logic3d_vector(63 downto 0);
  begin
    v_msc_result := msc_result;
    Verilog_Case_Ex := l3d_to_unsigned(op(0 + 1 downto 0));
    case Verilog_Case_Ex is
      when "00" =>
        v_msc_result(0 + 31 downto 0) := l3d_and(a(0 + 31 downto 0), b(0 + 31 downto 0));
      when "01" =>
        v_msc_result(0 + 31 downto 0) := l3d_or(a(0 + 31 downto 0), b(0 + 31 downto 0));
      when "10" =>
        v_msc_result(0 + 31 downto 0) := l3d_xor(a(0 + 31 downto 0), b(0 + 31 downto 0));
      when "11" =>
        v_msc_result(0 + 31 downto 0) := a(0 + 31 downto 0) sll l3d_shcount(b(0 + 4 downto 0));
      when others =>
        null;
    end case;
    msc_result(0 + 31 downto 0) <= v_msc_result(0 + 31 downto 0);
  end process;

  -- Generated from always process in g_msc_result[1]
  process (op, a, b) is
    variable Verilog_Case_Ex : unsigned(1 downto 0);
    variable v_msc_result : logic3d_vector(63 downto 0);
  begin
    v_msc_result := msc_result;
    Verilog_Case_Ex := l3d_to_unsigned(op(2 + 1 downto 2));
    case Verilog_Case_Ex is
      when "00" =>
        v_msc_result(32 + 31 downto 32) := l3d_and(b(0 + 31 downto 0), a(0 + 31 downto 0));
      when "01" =>
        v_msc_result(32 + 31 downto 32) := l3d_or(b(0 + 31 downto 0), a(0 + 31 downto 0));
      when "10" =>
        v_msc_result(32 + 31 downto 32) := l3d_xor(b(0 + 31 downto 0), a(0 + 31 downto 0));
      when "11" =>
        v_msc_result(32 + 31 downto 32) := b(0 + 31 downto 0) sll l3d_shcount(a(0 + 4 downto 0));
      when others =>
        null;
    end case;
    msc_result(32 + 31 downto 32) <= v_msc_result(32 + 31 downto 32);
  end process;

  comb_fused_0: process (msc_result) is
  begin
    y_c := l3d_xor(msc_result(32 + 31 downto 32), msc_result(0 + 31 downto 0));
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
