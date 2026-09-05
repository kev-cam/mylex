-- Item 8 (found by the ALU census after items 1-5): a dynamic part-select
-- read `a(To_Integer(t) + 31 downto To_Integer(t))` — tgt-vhdl's rendering
-- of `alu_in1[i*32 +: 32]` with the scaled index in a temporary signal
-- (alu.vhd:2868-2885 lane operand selects, 2974 br_result).  HEAD folds only
-- constant bounds: `slice-bounds k3/k3`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r8_dynslice is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r8_dynslice is
  signal alu_result_r : logic3d_vector(63 downto 0) := (others => L3D_X);
  signal last_tid_r : logic3d := L3D_X;
  signal tmp_ivl_189 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_192 : logic3d_vector(30 downto 0) := (others => L3D_X);
  signal tmp_ivl_193 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_196 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal br_result : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  comb_fused_12: process (a, b, op) is
  begin
    alu_result_r := a & b;
    last_tid_r := op(0);
    tmp_ivl_192 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_193 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_189 := tmp_ivl_192 & last_tid_r;
    tmp_ivl_196 := to_l3d(Resize(tmp_ivl_189 * tmp_ivl_193, 32), 32);
    br_result := alu_result_r(To_Integer(tmp_ivl_196) + 31 downto To_Integer(tmp_ivl_196));
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= br_result;
      end if;
    end if;
  end process;
end architecture;
