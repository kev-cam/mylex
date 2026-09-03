-- Self-check for signedidx.v against what vvp prints for the same stimulus:
--   x = 16'h8001: i=-1 -> y=x, i=0 -> y=1, i=7 -> y=0, i=-8 -> y=x;
--   sel=0 -> w=1, sel=1 -> w=0;  u=15 -> v=1, u=8 -> v=0.
library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_signedidx is end;
architecture sim of tb_signedidx is
  signal i, u : logic3d_vector(3 downto 0);
  signal sel : logic3d;
  signal x : logic3d_vector(15 downto 0);
  signal y, w, v : logic3d;
begin
  dut : entity work.top port map (i => i, sel => sel, u => u, x => x, y => y, w => w, v => v);
  process
  begin
    x <= to_l3d(16#8001#, 16); sel <= L3D_0; i <= to_l3d(15, 4); u <= to_l3d(15, 4);
    wait for 1 ns;
    assert y = L3D_X report "i=-1: y should be x (out of range)" severity failure;
    assert w = L3D_1 report "sel=0: w should be 1" severity failure;
    assert v = L3D_1 report "u=15: v should be 1" severity failure;
    sel <= L3D_1; i <= to_l3d(0, 4); u <= to_l3d(8, 4);
    wait for 1 ns;
    assert y = L3D_1 report "i=0: y should be 1" severity failure;
    assert w = L3D_0 report "sel=1: w should be 0" severity failure;
    assert v = L3D_0 report "u=8: v should be 0" severity failure;
    i <= to_l3d(7, 4);
    wait for 1 ns;
    assert y = L3D_0 report "i=7: y should be 0" severity failure;
    i <= to_l3d(8, 4);
    wait for 1 ns;
    assert y = L3D_X report "i=-8: y should be x (out of range)" severity failure;
    report "PASS signedidx";
    wait;
  end process;
end;
