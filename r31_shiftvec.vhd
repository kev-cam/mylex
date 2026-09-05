-- array-of-vector CLOCKED shift register: sr(i) <= sr(i-1). If the walker
-- composes the per-element NBA writes with BLOCKING order (read-just-written)
-- into one whole-array hold temp, the shift collapses to depth-1.
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r31_shiftvec is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r31_shiftvec is
  type sr_Type is array (3 downto 0) of logic3d_vector(7 downto 0);
  signal sr : sr_Type := (others => (others => L3D_0));
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  process is
  begin
    if rising_edge(clk) then
      sr(0) <= a(7 downto 0);
      sr(1) <= sr(0);
      sr(2) <= sr(1);
      sr(3) <= sr(2);
    end if;
    wait on clk;
  end process;
  yr <= sr(3) & sr(2) & sr(1) & sr(0);
end architecture;
