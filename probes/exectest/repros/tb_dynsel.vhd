library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_dynsel is end;
architecture sim of tb_dynsel is
  signal v : logic3d_vector(23 downto 0);
  signal sh : logic3d_vector(4 downto 0);   -- left x for the first delta
  signal y : logic3d;
  signal p : logic3d_vector(3 downto 0);

  function l3d(vv : std_logic_vector) return logic3d_vector is
    variable r : logic3d_vector(vv'range);
  begin
    for i in vv'range loop r(i) := to_logic3d(vv(i)); end loop;
    return r;
  end;
begin
  dut: entity work.top port map (v => v, sh => sh, y => y, p => p);
  process
  begin
    v <= l3d(x"00F0F5");
    wait for 1 ns;                 -- sh is x: must not be fatal, y/p read x
    assert y = L3D_X report "y with x index (expect x)" severity failure;
    sh <= l3d("00001"); wait for 1 ns;   -- idx = 0: y = v[0] = 1, p = v[3:0] = 5
    assert y = L3D_1 report "y idx0 (expect 1)" severity failure;
    assert p = l3d("0101") report "p idx0 (expect 0101)" severity failure;
    sh <= l3d("00101"); wait for 1 ns;   -- idx = 4: y = v[4] = 1, p = v[7:4] = F
    assert y = L3D_1 report "y idx4 (expect 1)" severity failure;
    assert p = l3d("1111") report "p idx4 (expect 1111)" severity failure;
    sh <= l3d("00000"); wait for 1 ns;   -- idx = 31: out of range -> x
    assert y = L3D_X report "y oob (expect x)" severity failure;
    assert p = l3d("XXXX") report "p oob (expect xxxx)" severity failure;
    report "PASS dynsel";
    wait;
  end process;
end;
