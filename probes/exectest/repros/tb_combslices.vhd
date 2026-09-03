library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

-- Self-check for combslices.v: two per-lane comb processes drive disjoint
-- constant slices of `data`; both lanes' bytes must come through.
entity tb_combslices is end;
architecture sim of tb_combslices is
  signal d, q : logic3d_vector(63 downto 0);
  signal align : logic3d_vector(3 downto 0);

  function l3d(v : std_logic_vector) return logic3d_vector is
    variable r : logic3d_vector(v'range);
  begin
    for i in v'range loop
      r(i) := to_logic3d(v(i));
    end loop;
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
  dut: entity work.top port map (d => d, align => align, q => q);
  process
  begin
    d <= l3d(x"89ABCDEF01234567");
    align <= l3d("0000"); wait for 1 ns;
    assert q = l3d(x"89ABCDEF01234567") report "align 0: " & h(q) severity failure;
    align <= l3d("0001"); wait for 1 ns;   -- lane0 shift 8 -> 0x23456767, lane1 unchanged
    assert q = l3d(x"89ABCDEF23456767") report "align 1: " & h(q) severity failure;
    align <= l3d("1000"); wait for 1 ns;   -- lane1 shift 16 -> 0xCDEFCDEF, lane0 unchanged
    assert q = l3d(x"CDEFCDEF01234567") report "align 8: " & h(q) severity failure;
    align <= l3d("1101"); wait for 1 ns;   -- lane1 shift 24 -> 0xEFABCDEF, lane0 shift 8
    assert q = l3d(x"EFABCDEF23456767") report "align 13: " & h(q) severity failure;
    report "PASS combslices";
    wait;
  end process;
end;
