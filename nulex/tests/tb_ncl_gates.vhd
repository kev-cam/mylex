-- tb_ncl_gates — exhaustive equivalence gate for the 2-input DIMS rules + INV.
-- For every (a,b) in {0,1}^2: DATA then NULL, and for each gate assert
-- ncl_decode(out) == the sync Boolean golden, out complete in DATA, out NULL in
-- the spacer.  Green == every rewrite rule refines its Boolean definition over
-- the whole input space with valid 4-phase RTZ behavior.
library IEEE;
use IEEE.std_logic_1164.all;
library ncl;
use ncl.ncl.all;

entity tb_ncl_gates is
end entity tb_ncl_gates;

architecture test of tb_ncl_gates is
  signal a, b : ncl_logic;
  signal z_inv, z_and, z_nand, z_or, z_nor, z_xor, z_xnor : ncl_logic;
  signal passes : integer := 0;

  procedure chk(signal z : in ncl_logic; g : in std_logic; nm : in string;
                va, vb : in std_logic) is
  begin
    assert ncl_is_data(z)
      report nm & " incomplete a=" & std_logic'image(va) & " b=" & std_logic'image(vb)
      severity failure;
    assert ncl_decode(z) = g
      report nm & " WRONG a=" & std_logic'image(va) & " b=" & std_logic'image(vb)
           & " got=" & std_logic'image(ncl_decode(z)) & " exp=" & std_logic'image(g)
      severity failure;
  end procedure;
begin
  u_inv:  entity work.ncl_inv   port map (a => a, z => z_inv);
  u_and:  entity work.ncl_and2  port map (a => a, b => b, z => z_and);
  u_nand: entity work.ncl_nand2 port map (a => a, b => b, z => z_nand);
  u_or:   entity work.ncl_or2   port map (a => a, b => b, z => z_or);
  u_nor:  entity work.ncl_nor2  port map (a => a, b => b, z => z_nor);
  u_xor:  entity work.ncl_xor2  port map (a => a, b => b, z => z_xor);
  u_xnor: entity work.ncl_xnor2 port map (a => a, b => b, z => z_xnor);

  stim: process
    type sl2 is array (0 to 1) of std_logic;
    constant v : sl2 := ('0', '1');
    variable va, vb : std_logic;
  begin
    a <= NCL_NULL; b <= NCL_NULL; wait for 10 ns;
    for ia in 0 to 1 loop
      for ib in 0 to 1 loop
        va := v(ia); vb := v(ib);
        a <= ncl_encode(va); b <= ncl_encode(vb); wait for 10 ns;
        chk(z_inv,  not va,            "INV",   va, vb);
        chk(z_and,  va and vb,         "AND2",  va, vb);
        chk(z_nand, not (va and vb),   "NAND2", va, vb);
        chk(z_or,   va or vb,          "OR2",   va, vb);
        chk(z_nor,  not (va or vb),    "NOR2",  va, vb);
        chk(z_xor,  va xor vb,         "XOR2",  va, vb);
        chk(z_xnor, not (va xor vb),   "XNOR2", va, vb);
        passes <= passes + 1;
        a <= NCL_NULL; b <= NCL_NULL; wait for 10 ns;
        assert ncl_is_null(z_and) and ncl_is_null(z_or) and ncl_is_null(z_xor)
             and ncl_is_null(z_inv)
          report "gate did not return to NULL" severity failure;
      end loop;
    end loop;
    report "GATES-GATE PASS: INV,AND2,NAND2,OR2,NOR2,XOR2,XNOR2 == sync golden over all inputs, 4-phase RTZ ("
         & integer'image(passes) & "/4)";
    wait;
  end process;
end architecture test;
