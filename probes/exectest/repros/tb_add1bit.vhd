library ieee;
use ieee.std_logic_1164.all;
library sv2vhdl;
use sv2vhdl.logic3d_types_pkg.all;

entity tb_add1bit is end;
architecture sim of tb_add1bit is
  signal a, b : logic3d := L3D_X;
  signal s, d, m, q, r, ps, pd, pm : logic3d;

  function chr(v : logic3d) return character is
  begin
    return to_char(v);
  end;
  procedure check(name : string; act, exp : logic3d) is
  begin
    assert act = exp
      report name & ": got '" & chr(act) & "' expected '" & chr(exp) & "'" severity failure;
  end;
  -- one input pair: 1-bit add/sub are XOR (carry dropped), multiply is AND,
  -- a/1 = a, a/0 = x, a mod 1 = 0, a mod 0 = x
  procedure pair(av, bv : logic3d; signal a, b : out logic3d) is
  begin
    a <= av; b <= bv;
  end;
begin
  dut: entity work.top port map (a => a, b => b, s => s, d => d, m => m, q => q, r => r,
                                 ps => ps, pd => pd, pm => pm);
  process
    type vec is array (0 to 3) of logic3d;
    constant av : vec := (L3D_0, L3D_1, L3D_0, L3D_1);
    constant bv : vec := (L3D_0, L3D_0, L3D_1, L3D_1);
    constant xs : vec := (L3D_0, L3D_1, L3D_1, L3D_0);   -- a xor b
    constant xm : vec := (L3D_0, L3D_0, L3D_0, L3D_1);   -- a and b
    constant xq : vec := (L3D_X, L3D_X, L3D_0, L3D_1);   -- a / b
    constant xr : vec := (L3D_X, L3D_X, L3D_0, L3D_0);   -- a mod b
  begin
    for i in 0 to 3 loop
      pair(av(i), bv(i), a, b);
      wait for 1 ns;
      check("s  " & integer'image(i), s,  xs(i));
      check("d  " & integer'image(i), d,  xs(i));
      check("m  " & integer'image(i), m,  xm(i));
      check("q  " & integer'image(i), q,  xq(i));
      check("r  " & integer'image(i), r,  xr(i));
      check("ps " & integer'image(i), ps, xs(i));
      check("pd " & integer'image(i), pd, xs(i));
      check("pm " & integer'image(i), pm, xm(i));
    end loop;
    -- an uncertain operand: the sv2vhdl arithmetic doctrine computes on the
    -- value plane (as the package's vector "+" does for every wider add), so
    -- the result is a CERTAIN bit, never the Z that the integer "+" produced
    pair(L3D_X, L3D_1, a, b);
    wait for 1 ns;
    assert is_strong(s) and not is_z(s) report "s with x operand is not a strong value: '" & chr(s) & "'" severity failure;
    assert is_strong(ps) and not is_z(ps) report "ps with x operand is not a strong value: '" & chr(ps) & "'" severity failure;
    report "PASS add1bit";
    wait;
  end process;
end;
