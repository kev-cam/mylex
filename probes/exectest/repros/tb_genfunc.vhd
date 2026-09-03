library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_genfunc is end;
architecture sim of tb_genfunc is
  signal a, z0, z1 : logic3d_vector(7 downto 0);
  signal y0 : logic3d_vector(3 downto 0);
  signal y1 : logic3d_vector(5 downto 0);

  function l3d(v : std_logic_vector) return logic3d_vector is
    variable r : logic3d_vector(v'range);
  begin
    for i in v'range loop r(i) := to_logic3d(v(i)); end loop;
    return r;
  end;
begin
  dut: entity work.top port map (a => a, y0 => y0, y1 => y1, z0 => z0, z1 => z1);
  process
  begin
    a <= l3d("10110101"); wait for 1 ns;
    assert y0 = l3d("0101")   report "y0 (expect 0101)" severity failure;
    assert y1 = l3d("110101") report "y1 (expect 110101)" severity failure;
    assert z0 = l3d("00000101") report "z0 (expect 00000101)" severity failure;
    assert z1 = l3d("00110101") report "z1 (expect 00110101)" severity failure;
    report "PASS genfunc";
    wait;
  end process;
end;
