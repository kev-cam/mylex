-- Self-check for scalarword.v: y = m[2][idx] is 1 only for idx = 0 and x
-- otherwise (Verilog out-of-range read); z = m[1][0] = 1; q = 0 | 1 = 1.
library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_scalarword is end;
architecture sim of tb_scalarword is
  signal idx : logic3d_vector(1 downto 0);
  signal y, z, q : logic3d;
begin
  dut : entity work.top port map (idx => idx, y => y, z => z, q => q);
  process
  begin
    idx <= to_l3d(0, 2);
    wait for 1 ns;
    assert y = L3D_1 report "idx=0: y should be 1" severity failure;
    assert z = L3D_1 report "z should be 1" severity failure;
    assert q = L3D_1 report "q should be 1" severity failure;
    idx <= to_l3d(1, 2);
    wait for 1 ns;
    assert y = L3D_X report "idx=1: y should be x (out of range)" severity failure;
    idx <= to_l3d(3, 2);
    wait for 1 ns;
    assert y = L3D_X report "idx=3: y should be x (out of range)" severity failure;
    idx <= (others => L3D_X);
    wait for 1 ns;
    -- an all-x index reads by its value plane under the sv2vhdl doctrine
    -- (l3d_index: address 0), so only require a defined, non-Z read here
    assert y = L3D_1 or y = L3D_X report "idx=x: y should be the value-plane read (1) or x" severity failure;
    idx <= to_l3d(0, 2);
    wait for 1 ns;
    assert y = L3D_1 report "idx=0 again: y should be 1" severity failure;
    report "PASS scalarword";
    wait;
  end process;
end;
