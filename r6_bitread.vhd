-- Item 6: l3d_bit_read on an unconstrained operator result.
-- VX_lane_dispatch's issue-index arithmetic reads bit i of the sum of two
-- resized lane indices (exec.vhd:13060, Tier A):
--   l3d_bit_read(unsigned_to_l3d(l3d_to_unsigned(a)) + unsigned_to_l3d(l3d_to_unsigned(b)), i)
-- The `+` result carries no bounds, so HEAD's r2_width(operand) is -1:
-- `bitread-width`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r6_bitread is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r6_bitread is
  signal tmp_ivl_9 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_15 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal issue_indices_0 : logic3d := L3D_X;
  signal issue_indices_1 : logic3d := L3D_X;
  signal issue_indices_2 : logic3d := L3D_X;
  signal issue_indices_3 : logic3d := L3D_X;
  signal y_c : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_0: process (a, b) is
  begin
    tmp_ivl_9 := a;
    tmp_ivl_15 := b;
    issue_indices_0 := l3d_bit_read(unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_9)) + unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_15)), 0);
    issue_indices_1 := l3d_bit_read(unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_9)) + unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_15)), 1);
    issue_indices_2 := l3d_bit_read(unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_9)) + unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_15)), 2);
    issue_indices_3 := l3d_bit_read(unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_9)) + unsigned_to_l3d(l3d_to_unsigned(tmp_ivl_15)), 31);
    y_c := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0) & issue_indices_3 & issue_indices_2 & issue_indices_1 & issue_indices_0;
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
