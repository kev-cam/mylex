-- Item 9 (Tier B census, 2818 of the ~4000 declines: vx_ks_adder G_g_KS /
-- P_g_KS, vx_find_first s_n / d_n, vx_fdivsqrt_unit srt_stage): an unpacked
-- array-of-vector SIGNAL used as a WIRE ARRAY.  Memory-shaped by type (7 x
-- 48-bit words) but every index is a constant: elements written whole by
-- continuous assigns G(5) <= .., read through nested constant selects
-- G(6)(46) / G(5)(7 downto 0), a dynamic bit read and a dynamic part read of
-- a constant word, a nested-select target in a clocked process, and the
-- (others => (others => L3D_X)) power-on fill.  Before: the signal became a
-- memory (cont-assign-target / array-ref@cont-rhs / comb-empty declines).
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r17_warr is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r17_warr is
  type G_Type is array (6 downto 0) of logic3d_vector(47 downto 0);
  type R_Type is array (0 to 2) of logic3d_vector(31 downto 0);
  signal G : G_Type := (others => (others => L3D_X));
  signal R : R_Type := (others => (others => L3D_0));
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
  signal t : logic3d := L3D_X;
  signal p : logic3d_vector(7 downto 0) := (others => L3D_X);
begin
  y <= yr;
  G(0) <= a & b(15 downto 0);
  G(1) <= b & a(15 downto 0);
  G(2) <= G(0)(47 downto 24) & G(1)(23 downto 0);
  G(3) <= G(2)(46 downto 0) & G(1)(47);
  G(4) <= G(3) xor G(2);
  G(5) <= G(4)(7 downto 0) & G(3)(7 downto 0) & G(2)(7 downto 0) & G(1)(7 downto 0) & G(0)(7 downto 0) & G(4)(15 downto 8);
  G(6) <= G(5)(23 downto 0) & G(4)(47 downto 24);
  t <= G(3)(l3d_index(op, false));                                        -- dynamic bit of a constant word
  p <= G(6)(l3d_index(op, false) + 7 downto l3d_index(op, false));         -- dynamic part of a constant word
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        R(0) <= (others => L3D_0);
        R(1) <= (others => L3D_0);
        R(2)(31 downto 16) <= (others => L3D_0);
        R(2)(15 downto 0) <= (others => L3D_0);
      else
        R(0) <= G(6)(31 downto 0);
        R(1) <= G(5)(47 downto 16) xor (G(4)(46) & G(4)(45) & G(6)(46) & G(0)(46) & R(0)(27 downto 0));
        R(2)(31 downto 16) <= R(1)(15 downto 0);
        R(2)(15 downto 8) <= p;
        R(2)(7 downto 0) <= t & t & t & t & G(2)(3 downto 0);
      end if;
    end if;
    wait on clk;
  end process;
  yr <= R(0) xor R(1) xor R(2);
end architecture;
