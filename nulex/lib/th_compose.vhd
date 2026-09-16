-- nulex/lib/th_compose.vhd — the TH cells that are NOT single sky130 gates,
-- COMPOSED from the leaf TH cells (th12/13/14/22/33, each -> one sky130 cell).
--
-- Hysteretic C-elements (th22/th33/th44 `composed`): a THmn with hysteresis is
--   y = set(inputs) OR (y AND any(inputs))
-- where set = the m-of-n threshold and any = OR of all inputs. set=1 -> y=1;
-- all inputs 0 -> y=0; otherwise HOLD. (For 2-in this is the Muller C-element,
-- = maj3(a,b,y).) The feedback net is the state — the physical realization is a
-- small sky130 cell cluster with one feedback wire.
--
-- Weighted / threshold gates (th34w2/th23w2/th24/th34 `composed`), used by the
-- Fant adder, are Boolean compositions of and/or (= th22/33/44 and th12/13/14).

library IEEE; use IEEE.std_logic_1164.all;

-- ===== hysteretic C-elements =================================================
architecture composed of th22 is             -- Muller C-element (2-of-2 + hold)
  signal s, r, h, yi : std_logic;
begin
  us : entity work.th22(comb) port map (a => a,  b => b, y => s);   -- set = a&b
  ur : entity work.th12(comb) port map (a => a,  b => b, y => r);   -- any = a|b
  uh : entity work.th22(comb) port map (a => yi, b => r, y => h);   -- hold = y & any
  uy : entity work.th12(comb) port map (a => s,  b => h, y => yi);  -- y = set | hold  (feedback)
  y <= yi;
end architecture composed;

library IEEE; use IEEE.std_logic_1164.all;
architecture composed of th33 is             -- 3-of-3 with hysteresis
  signal s, r, h, yi : std_logic;
begin
  us : entity work.th33(comb) port map (a => a,  b => b, c => c, y => s);   -- a&b&c
  ur : entity work.th13(comb) port map (a => a,  b => b, c => c, y => r);   -- a|b|c
  uh : entity work.th22(comb) port map (a => yi, b => r, y => h);
  uy : entity work.th12(comb) port map (a => s,  b => h, y => yi);
  y <= yi;
end architecture composed;

library IEEE; use IEEE.std_logic_1164.all;
architecture composed of th44 is             -- 4-of-4 with hysteresis
  signal s, r, h, yi : std_logic;
begin
  us : entity work.th44(comb) port map (a => a,  b => b, c => c, d => d, y => s);
  ur : entity work.th14(comb) port map (a => a,  b => b, c => c, d => d, y => r);
  uh : entity work.th22(comb) port map (a => yi, b => r, y => h);
  uy : entity work.th12(comb) port map (a => s,  b => h, y => yi);
  y <= yi;
end architecture composed;

-- ===== weighted / threshold (combinational) ==================================
library IEEE; use IEEE.std_logic_1164.all;
architecture composed of th23w2 is           -- a | (b&c)  (a has weight 2)
  signal t : std_logic;
begin
  u1 : entity work.th22(comb) port map (a => b, b => c, y => t);
  u2 : entity work.th12(comb) port map (a => a, b => t, y => y);
end architecture composed;

library IEEE; use IEEE.std_logic_1164.all;
architecture composed of th34w2 is           -- (a&(b|c|d)) | (b&c&d)
  signal t1, t2, t3 : std_logic;
begin
  u1 : entity work.th13(comb) port map (a => b, b => c, c => d, y => t1);   -- b|c|d
  u2 : entity work.th22(comb) port map (a => a, b => t1, y => t2);          -- a&(b|c|d)
  u3 : entity work.th33(comb) port map (a => b, b => c, c => d, y => t3);   -- b&c&d
  uy : entity work.th12(comb) port map (a => t2, b => t3, y => y);
end architecture composed;

library IEEE; use IEEE.std_logic_1164.all;
architecture composed of th24 is             -- 2-of-4 = OR of the 6 pairwise ANDs
  signal p1, p2, p3, p4, p5, p6, o1, o2 : std_logic;
begin
  a1 : entity work.th22(comb) port map (a => a, b => b, y => p1);
  a2 : entity work.th22(comb) port map (a => a, b => c, y => p2);
  a3 : entity work.th22(comb) port map (a => a, b => d, y => p3);
  a4 : entity work.th22(comb) port map (a => b, b => c, y => p4);
  a5 : entity work.th22(comb) port map (a => b, b => d, y => p5);
  a6 : entity work.th22(comb) port map (a => c, b => d, y => p6);
  o_1 : entity work.th13(comb) port map (a => p1, b => p2, c => p3, y => o1);
  o_2 : entity work.th13(comb) port map (a => p4, b => p5, c => p6, y => o2);
  uy  : entity work.th12(comb) port map (a => o1, b => o2, y => y);
end architecture composed;

library IEEE; use IEEE.std_logic_1164.all;
architecture composed of th34 is             -- 3-of-4 = OR of the 4 triple ANDs
  signal t1, t2, t3, t4 : std_logic;
begin
  a1 : entity work.th33(comb) port map (a => a, b => b, c => c, y => t1);
  a2 : entity work.th33(comb) port map (a => a, b => b, c => d, y => t2);
  a3 : entity work.th33(comb) port map (a => a, b => c, c => d, y => t3);
  a4 : entity work.th33(comb) port map (a => b, b => c, c => d, y => t4);
  uy : entity work.th14(comb) port map (a => t1, b => t2, c => t3, d => t4, y => y);
end architecture composed;
