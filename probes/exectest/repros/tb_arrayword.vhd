library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_arrayword is end;
architecture sim of tb_arrayword is
  signal a, b, y, w : logic3d_vector(7 downto 0);
  signal z : logic3d;

  function l3d(v : std_logic_vector) return logic3d_vector is
    variable r : logic3d_vector(v'range);
  begin
    for i in v'range loop r(i) := to_logic3d(v(i)); end loop;
    return r;
  end;
  function h(v : logic3d_vector) return string is
    variable s : string(1 to v'length);
  begin
    for i in v'range loop
      case v(i) is
        when L3D_0 => s(v'length - i) := '0';
        when L3D_1 => s(v'length - i) := '1';
        when others => s(v'length - i) := 'x';
      end case;
    end loop;
    return s;
  end;
begin
  dut: entity work.top port map (a => a, b => b, y => y, z => z, w => w);
  process
  begin
    a <= l3d(x"A5"); b <= l3d(x"3C"); wait for 1 ns;
    -- y = A[1] = b
    assert y = l3d(x"3C") report "y: " & h(y) severity failure;
    -- z = b[3] ^ a[5] = 1 ^ 1 = 0
    assert z = L3D_0 report "z (expect 0)" severity failure;
    -- w = {a[7:4], b[3:0]} = 0xAC
    assert w = l3d(x"AC") report "w: " & h(w) severity failure;
    a <= l3d(x"0F"); b <= l3d(x"F0"); wait for 1 ns;
    -- z = b[3] ^ a[5] = 0 ^ 0 = 0 ; w = {0, 0} = 0x00 ; y = F0
    assert y = l3d(x"F0") report "y2: " & h(y) severity failure;
    assert z = L3D_0 report "z2 (expect 0)" severity failure;
    assert w = l3d(x"00") report "w2: " & h(w) severity failure;
    a <= l3d(x"20"); b <= l3d(x"08"); wait for 1 ns;
    -- z = b[3] ^ a[5] = 1 ^ 1 = 0 ; a=0x20 -> a[5]=1, b=0x08 -> b[3]=1
    assert z = L3D_0 report "z3 (expect 0)" severity failure;
    a <= l3d(x"00"); b <= l3d(x"08"); wait for 1 ns;
    -- z = 1 ^ 0 = 1
    assert z = L3D_1 report "z4 (expect 1)" severity failure;
    report "PASS arrayword";
    wait;
  end process;
end;
