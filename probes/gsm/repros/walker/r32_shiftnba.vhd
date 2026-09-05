-- tgt-vhdl NBA-shadow idiom for an array-of-vector shift register: pre-copy
-- the whole array into a variable, write elements from earlier elements,
-- commit. If per-element writes compose with BLOCKING order (v(i):=v(i-1)
-- reads the JUST-WRITTEN v(i-1)), the shift collapses to depth-1.
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r32_shiftnba is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r32_shiftnba is
  type sr_Type is array (3 downto 0) of logic3d_vector(7 downto 0);
  signal sr : sr_Type := (others => (others => L3D_0));
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  process is
    variable v_nba_sr : sr_Type;
    variable nba_init_run : Boolean := True;
  begin
    v_nba_sr := sr;
    if rising_edge(clk) then
      v_nba_sr(3) := v_nba_sr(2);
      v_nba_sr(2) := v_nba_sr(1);
      v_nba_sr(1) := v_nba_sr(0);
      v_nba_sr(0) := a(7 downto 0);
    end if;
    if nba_init_run then nba_init_run := False; else wait for 0 ns; end if;
    sr <= v_nba_sr;
    wait on clk;
  end process;
  yr <= sr(3) & sr(2) & sr(1) & sr(0);
end architecture;
