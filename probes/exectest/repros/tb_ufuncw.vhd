library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_ufuncw is end;
architecture sim of tb_ufuncw is
  signal wide : logic3d_vector(5 downto 0);
  signal narrow : logic3d_vector(1 downto 0);
  signal y1, y2 : logic3d_vector(3 downto 0);

  function l3d(v : std_logic_vector) return logic3d_vector is
    variable r : logic3d_vector(v'range);
  begin
    for i in v'range loop r(i) := to_logic3d(v(i)); end loop;
    return r;
  end;
begin
  dut: entity work.top port map (wide => wide, narrow => narrow, y1 => y1, y2 => y2);
  process
  begin
    wide <= l3d("110101"); narrow <= l3d("10"); wait for 1 ns;
    assert y1 = l3d("0101") report "y1 (expect 0101)" severity failure;
    assert y2 = l3d("0010") report "y2 (expect 0010)" severity failure;
    wide <= l3d("001110"); narrow <= l3d("11"); wait for 1 ns;
    assert y1 = l3d("1110") report "y1b (expect 1110)" severity failure;
    assert y2 = l3d("0011") report "y2b (expect 0011)" severity failure;
    report "PASS ufuncw";
    wait;
  end process;
end;
