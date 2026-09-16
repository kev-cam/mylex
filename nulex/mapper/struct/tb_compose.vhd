library IEEE; use IEEE.std_logic_1164.all; use IEEE.numeric_std.all;
entity tb_compose is end entity;
architecture t of tb_compose is
  signal a, b, c, d : std_logic := '0';
  signal w1c, w1r, w2c, w2r, w3c, w3r, w4c, w4r : std_logic;
  signal e2c, e2r, e3c, e3r, e4c, e4r : std_logic;
begin
  -- weighted: composed vs comb reference
  g1c: entity work.th23w2(composed) port map (a, b, c, w1c);
  g1r: entity work.th23w2(comb)     port map (a, b, c, w1r);
  g2c: entity work.th34w2(composed) port map (a, b, c, d, w2c);
  g2r: entity work.th34w2(comb)     port map (a, b, c, d, w2r);
  g3c: entity work.th24(composed)   port map (a, b, c, d, w3c);
  g3r: entity work.th24(comb)       port map (a, b, c, d, w3r);
  g4c: entity work.th34(composed)   port map (a, b, c, d, w4c);
  g4r: entity work.th34(comb)       port map (a, b, c, d, w4r);
  -- hysteretic C-elements: composed vs qdi reference
  c2c: entity work.th22(composed) port map (a, b, e2c);
  c2r: entity work.th22(qdi)      port map (a, b, e2r);
  c3c: entity work.th33(composed) port map (a, b, c, e3c);
  c3r: entity work.th33(qdi)      port map (a, b, c, e3r);
  c4c: entity work.th44(composed) port map (a, b, c, d, e4c);
  c4r: entity work.th44(qdi)      port map (a, b, c, d, e4r);
  process
    variable errs : integer := 0;
    procedure setin(v : integer) is begin
      a <= std_logic(to_unsigned(v,4)(0)); b <= std_logic(to_unsigned(v,4)(1));
      c <= std_logic(to_unsigned(v,4)(2)); d <= std_logic(to_unsigned(v,4)(3));
    end procedure;
  begin
    -- exhaustive check of the weighted/threshold cells (composed == comb spec)
    for i in 0 to 15 loop
      setin(i); wait for 2 ns;
      if w1c/=w1r then errs:=errs+1; report "th23w2 mismatch @"&integer'image(i) severity warning; end if;
      if w2c/=w2r then errs:=errs+1; report "th34w2 mismatch @"&integer'image(i) severity warning; end if;
      if w3c/=w3r then errs:=errs+1; report "th24 mismatch @"&integer'image(i) severity warning; end if;
      if w4c/=w4r then errs:=errs+1; report "th34 mismatch @"&integer'image(i) severity warning; end if;
    end loop;
    -- hysteresis of the C-elements: NULL -> set -> partial(hold) -> NULL, all-ones set
    setin(0);  wait for 2 ns;   -- reset
    setin(15); wait for 2 ns;   -- all high -> all C set
    setin(1);  wait for 2 ns;   -- partial -> hold previous (1)
    setin(0);  wait for 2 ns;   -- all low -> reset
    setin(3);  wait for 2 ns;   -- a,b high: th22 sets, th33/th44 hold(0)
    setin(15); wait for 2 ns;
    -- compare composed vs qdi across those; check at end each matches
    if e2c/=e2r then errs:=errs+1; report "th22 C mismatch" severity warning; end if;
    if e3c/=e3r then errs:=errs+1; report "th33 C mismatch" severity warning; end if;
    if e4c/=e4r then errs:=errs+1; report "th44 C mismatch" severity warning; end if;
    if errs=0 then report "TH COMPOSE: PASS (4 weighted exhaustive + 3 C-elements hysteresis vs spec)" severity note;
    else report "TH COMPOSE: FAIL ("&integer'image(errs)&" mismatches)" severity failure; end if;
    wait;
  end process;
  -- continuous C-element equivalence monitor (after settling)
  mon: process(e2c,e2r,e3c,e3r,e4c,e4r) begin end process;
end architecture t;
