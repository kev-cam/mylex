-- The first real Tier B build through the walker (all 119 modules
-- admitted) mismatched on the FPU commit data from cycle 13: the
-- normalisation count.  VX_find_first is a reduction tree over a wire
-- array `d_n : array (62 downto 0) of logic3d_vector(4 downto 0)`, one
-- comb process per tree node writing ONE element from its two children:
--     process (all) is begin
--       if is_one(s_n(2*i+1)) then d_n(i) <= d_n(2*i+1);
--       else d_n(i) <= d_n(2*i+2); end if;
--     end process;
-- The flat-wire lowering gave every node a hold temp for the WHOLE array
-- rooted at the array itself and committed the whole wire, so 31
-- processes contended for one wire through self-rooted temps.  A comb
-- process that writes only a constant sub-range now drives exactly that
-- range.  Below: a 7-node tree over the leaves a(3..0)/b(3..0) with the
-- register reading the root.
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r22_ffirst is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r22_ffirst is
  type d_n_Type is array (6 downto 0) of logic3d_vector(7 downto 0);
  signal d_n : d_n_Type := (others => (others => L3D_X));
  type s_n_Type is array (6 downto 0) of logic3d;
  signal s_n : s_n_Type;
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  -- leaves 3..6 (lone assigns: connects)
  s_n(3) <= op(0);  d_n(3) <= a(7 downto 0);
  s_n(4) <= op(1);  d_n(4) <= a(15 downto 8);
  s_n(5) <= op(2);  d_n(5) <= b(7 downto 0);
  s_n(6) <= op(3);  d_n(6) <= b(15 downto 8);
  -- nodes 2, 1, 0 (one comb process per node, element writes)
  process (all) is
  begin
    if is_one(s_n(5)) then d_n(2) <= d_n(5); else d_n(2) <= d_n(6); end if;
  end process;
  s_n(2) <= l3d_or(s_n(5), s_n(6));
  process (all) is
  begin
    if is_one(s_n(3)) then d_n(1) <= d_n(3); else d_n(1) <= d_n(4); end if;
  end process;
  s_n(1) <= l3d_or(s_n(3), s_n(4));
  process (all) is
  begin
    if is_one(s_n(1)) then d_n(0) <= d_n(1); else d_n(0) <= d_n(2); end if;
  end process;
  s_n(0) <= l3d_or(s_n(1), s_n(2));
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        yr <= (others => L3D_0);
      else
        yr <= (b(31 downto 16) & d_n(0) & d_n(1)) xor (a(31 downto 1) & s_n(0));
      end if;
    end if;
    wait on clk;
  end process;
end architecture;
