-- nulex/lib/th_cells.vhd — instantiable threshold (TH) gate cells.
--
-- The nvc lib/ncl th* are combinational FUNCTIONS, so any synthesis inlines them
-- and no TH cell survives in the netlist (the structural DIMS expansion collapses
-- to $and/$or). These are the same gates as ENTITIES, so a structural NCL netlist
-- (map_ncl_struct.py) keeps them as first-class instances — for physical lowering
-- and for isochronic-fork extraction (constraints.py sees the TH cells).
--
-- MULTIPLE VERSIONS (ASYNC-PLAN binding layer): each cell has two architectures.
--   comb : stateless Boolean model, identical to nvc lib/ncl th* — for functional
--          simulation and equivalence checking (fast, no NULL cycling needed).
--   qdi  : the real hysteretic C-element — output asserts when the (weighted)
--          threshold is met and HOLDS until ALL inputs return to 0 (NULL). This
--          is the delay-insensitive behavior; NULL/DATA alternation is required.
-- A third binding (phys, SG13G2/logic3da) is future work; pick the architecture
-- per instance with a VHDL configuration or `entity work.thNN(comb|qdi)`.
--
-- Ports: single std_logic per rail (a dual-rail NCL signal is two of these).
-- THmn asserts on m of n; THmnw2 gives input `a` weight 2. Threshold-1 gates
-- (th12/th13/th14) are plain OR — no hysteresis is possible for 1-of-n (it
-- deasserts exactly when every input is 0), so their two architectures coincide.

library IEEE; use IEEE.std_logic_1164.all;

-- ---- helper: hysteretic core is inlined per entity (no shared generic to keep
--      each cell a clean, individually-bindable unit) ----

-- ===== threshold-1 collectors (OR); comb == qdi ==============================
entity th12 is port (a, b : in std_logic; y : out std_logic); end entity;
architecture comb of th12 is begin y <= a or b; end architecture;
architecture qdi  of th12 is begin y <= a or b; end architecture;

library IEEE; use IEEE.std_logic_1164.all;
entity th13 is port (a, b, c : in std_logic; y : out std_logic); end entity;
architecture comb of th13 is begin y <= a or b or c; end architecture;
architecture qdi  of th13 is begin y <= a or b or c; end architecture;

library IEEE; use IEEE.std_logic_1164.all;
entity th14 is port (a, b, c, d : in std_logic; y : out std_logic); end entity;
architecture comb of th14 is begin y <= a or b or c or d; end architecture;
architecture qdi  of th14 is begin y <= a or b or c or d; end architecture;

-- ===== TH22 (C-element, 2 of 2) ==============================================
library IEEE; use IEEE.std_logic_1164.all;
entity th22 is port (a, b : in std_logic; y : out std_logic); end entity;
architecture comb of th22 is begin y <= a and b; end architecture;
architecture qdi of th22 is
begin
  process (a, b)
    variable st : std_logic := '0';
  begin
    if a = '1' and b = '1' then st := '1';          -- threshold met -> set
    elsif a = '0' and b = '0' then st := '0';       -- all NULL -> reset
    end if;                                          -- else HOLD (hysteresis)
    y <= st;
  end process;
end architecture qdi;

-- ===== TH13-as-C? no; TH23 (majority, 2 of 3) ================================
library IEEE; use IEEE.std_logic_1164.all;
entity th23 is port (a, b, c : in std_logic; y : out std_logic); end entity;
architecture comb of th23 is begin y <= (a and b) or (a and c) or (b and c); end architecture;
architecture qdi of th23 is
begin
  process (a, b, c)
    variable st : std_logic := '0';
    variable n  : integer;
  begin
    n := 0;
    if a = '1' then n := n + 1; end if;
    if b = '1' then n := n + 1; end if;
    if c = '1' then n := n + 1; end if;
    if n >= 2 then st := '1'; elsif n = 0 then st := '0'; end if;
    y <= st;
  end process;
end architecture qdi;

-- ===== TH33 (3 of 3) =========================================================
library IEEE; use IEEE.std_logic_1164.all;
entity th33 is port (a, b, c : in std_logic; y : out std_logic); end entity;
architecture comb of th33 is begin y <= a and b and c; end architecture;
architecture qdi of th33 is
begin
  process (a, b, c)
    variable st : std_logic := '0';
  begin
    if a = '1' and b = '1' and c = '1' then st := '1';
    elsif a = '0' and b = '0' and c = '0' then st := '0';
    end if;
    y <= st;
  end process;
end architecture qdi;

-- ===== TH24 / TH34 / TH44 (2,3,4 of 4) =======================================
library IEEE; use IEEE.std_logic_1164.all;
entity th24 is port (a, b, c, d : in std_logic; y : out std_logic); end entity;
architecture comb of th24 is
  function cnt(a,b,c,d:std_logic) return integer is variable n:integer:=0; begin
    if a='1' then n:=n+1; end if; if b='1' then n:=n+1; end if;
    if c='1' then n:=n+1; end if; if d='1' then n:=n+1; end if; return n; end;
begin y <= '1' when cnt(a,b,c,d) >= 2 else '0'; end architecture;
architecture qdi of th24 is
begin
  process (a, b, c, d)
    variable st : std_logic := '0'; variable n : integer;
  begin
    n := 0;
    if a='1' then n:=n+1; end if; if b='1' then n:=n+1; end if;
    if c='1' then n:=n+1; end if; if d='1' then n:=n+1; end if;
    if n >= 2 then st := '1'; elsif n = 0 then st := '0'; end if;
    y <= st;
  end process;
end architecture qdi;

library IEEE; use IEEE.std_logic_1164.all;
entity th34 is port (a, b, c, d : in std_logic; y : out std_logic); end entity;
architecture comb of th34 is
  function cnt(a,b,c,d:std_logic) return integer is variable n:integer:=0; begin
    if a='1' then n:=n+1; end if; if b='1' then n:=n+1; end if;
    if c='1' then n:=n+1; end if; if d='1' then n:=n+1; end if; return n; end;
begin y <= '1' when cnt(a,b,c,d) >= 3 else '0'; end architecture;
architecture qdi of th34 is
begin
  process (a, b, c, d)
    variable st : std_logic := '0'; variable n : integer;
  begin
    n := 0;
    if a='1' then n:=n+1; end if; if b='1' then n:=n+1; end if;
    if c='1' then n:=n+1; end if; if d='1' then n:=n+1; end if;
    if n >= 3 then st := '1'; elsif n = 0 then st := '0'; end if;
    y <= st;
  end process;
end architecture qdi;

library IEEE; use IEEE.std_logic_1164.all;
entity th44 is port (a, b, c, d : in std_logic; y : out std_logic); end entity;
architecture comb of th44 is begin y <= a and b and c and d; end architecture;
architecture qdi of th44 is
begin
  process (a, b, c, d)
    variable st : std_logic := '0';
  begin
    if a='1' and b='1' and c='1' and d='1' then st := '1';
    elsif a='0' and b='0' and c='0' and d='0' then st := '0';
    end if;
    y <= st;
  end process;
end architecture qdi;

-- ===== weighted: TH23w2, TH34w2 (input a has weight 2) =======================
library IEEE; use IEEE.std_logic_1164.all;
entity th23w2 is port (a, b, c : in std_logic; y : out std_logic); end entity;
architecture comb of th23w2 is begin y <= a or (b and c); end architecture;
architecture qdi of th23w2 is
begin
  process (a, b, c)
    variable st : std_logic := '0'; variable w : integer;
  begin
    w := 0;
    if a = '1' then w := w + 2; end if;
    if b = '1' then w := w + 1; end if;
    if c = '1' then w := w + 1; end if;
    if w >= 2 then st := '1'; elsif w = 0 then st := '0'; end if;
    y <= st;
  end process;
end architecture qdi;

library IEEE; use IEEE.std_logic_1164.all;
entity th34w2 is port (a, b, c, d : in std_logic; y : out std_logic); end entity;
architecture comb of th34w2 is begin y <= (a and (b or c or d)) or (b and c and d); end architecture;
architecture qdi of th34w2 is
begin
  process (a, b, c, d)
    variable st : std_logic := '0'; variable w : integer;
  begin
    w := 0;
    if a = '1' then w := w + 2; end if;
    if b = '1' then w := w + 1; end if;
    if c = '1' then w := w + 1; end if;
    if d = '1' then w := w + 1; end if;
    if w >= 3 then st := '1'; elsif w = 0 then st := '0'; end if;
    y <= st;
  end process;
end architecture qdi;
