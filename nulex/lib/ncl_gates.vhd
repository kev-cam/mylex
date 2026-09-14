-- nulex/lib/ncl_gates.vhd — correct-by-construction dual-rail NCL gate expansions.
--
-- These are the P3 rewrite-rule TARGETS: one entity per yosys/abc primitive
-- ({AND,NAND,OR,NOR,XOR,XNOR,MUX} + DFF), each a structural dual-rail netlist
-- built ONLY from NCL threshold gates (nvc lib/ncl th* functions), so each is
-- input-complete + observable by construction and lowers to physical TH cells.
--
-- Rail convention (nvc lib/ncl, verified against the code, NOT the stale
-- comments): value rides the .L rail. DATA1=(L=1,H=0), DATA0=(L=0,H=1),
-- NULL=(0,0). So .L = "value-is-1 rail" (t), .H = "value-is-0 rail" (f).
-- The physical QDI binding inserts a documented L<->H swap for the SG13G2 SPICE
-- cells (which carry value on H); the IR/sim convention stays L.
--
-- DIMS (Delay-Insensitive Minterm Synthesis) template for a 2-input gate:
--   form the 4 minterms with TH22 C-elements, one per input-rail combination
--   (each needs BOTH inputs DATA => input-complete), then collect the minterms
--   whose Boolean result is 1 onto the output's t-rail and the rest onto its
--   f-rail (each minterm feeds exactly one output => observable). Exactly one
--   minterm fires per DATA input, so the rail collectors are plain OR.
--
-- Congruence lemma (per rule, informal here; the machine-checked obligation is
-- ASYNC-PLAN §4): given both inputs are well-formed dual-rail (exactly one rail
-- asserted in DATA, both low in NULL), the output is well-formed dual-rail,
-- decodes to the gate's Boolean function of the decoded inputs, asserts only
-- after both inputs are DATA, and returns to NULL only after both are NULL.

-- ===========================================================================
-- ncl_and2 — DIMS AND2.  Z = a AND b.
--   minterms: m11=TH22(a.t,b.t) m10=TH22(a.t,b.f) m01=TH22(a.f,b.t) m00=TH22(a.f,b.f)
--   Z.t (=1) = m11                     [a=1 & b=1]
--   Z.f (=0) = m10 or m01 or m00       [any input 0]
-- ===========================================================================
library IEEE;
use IEEE.std_logic_1164.all;
library ncl;
use ncl.ncl.all;

entity ncl_and2 is
  port ( a, b : in ncl_logic; z : out ncl_logic );
end entity ncl_and2;

architecture dims of ncl_and2 is
  signal m11, m10, m01, m00 : std_logic;
begin
  m11 <= th22(a.L, b.L);   -- a=1,b=1
  m10 <= th22(a.L, b.H);   -- a=1,b=0
  m01 <= th22(a.H, b.L);   -- a=0,b=1
  m00 <= th22(a.H, b.H);   -- a=0,b=0
  z.L <= m11;                       -- value-1 rail
  z.H <= m10 or m01 or m00;         -- value-0 rail
end architecture dims;

-- The remaining 2-input gates share the SAME 4 minterms; only the rail
-- collectors differ (which minterms make the output 1 vs 0). Each is
-- input-complete (every minterm is a TH22 C-element needing both inputs DATA)
-- and observable (every minterm feeds exactly one output rail).

-- ncl_nand2 : Z = NOT(a AND b)  -- AND with rails swapped
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_nand2 is port ( a, b : in ncl_logic; z : out ncl_logic ); end entity;
architecture dims of ncl_nand2 is signal m11,m10,m01,m00 : std_logic; begin
  m11<=th22(a.L,b.L); m10<=th22(a.L,b.H); m01<=th22(a.H,b.L); m00<=th22(a.H,b.H);
  z.L <= m10 or m01 or m00;   z.H <= m11;
end architecture dims;

-- ncl_or2 : Z = a OR b
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_or2 is port ( a, b : in ncl_logic; z : out ncl_logic ); end entity;
architecture dims of ncl_or2 is signal m11,m10,m01,m00 : std_logic; begin
  m11<=th22(a.L,b.L); m10<=th22(a.L,b.H); m01<=th22(a.H,b.L); m00<=th22(a.H,b.H);
  z.L <= m11 or m10 or m01;   z.H <= m00;
end architecture dims;

-- ncl_nor2 : Z = NOT(a OR b)  -- OR with rails swapped
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_nor2 is port ( a, b : in ncl_logic; z : out ncl_logic ); end entity;
architecture dims of ncl_nor2 is signal m11,m10,m01,m00 : std_logic; begin
  m11<=th22(a.L,b.L); m10<=th22(a.L,b.H); m01<=th22(a.H,b.L); m00<=th22(a.H,b.H);
  z.L <= m00;   z.H <= m11 or m10 or m01;
end architecture dims;

-- ncl_xor2 : Z = a XOR b
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_xor2 is port ( a, b : in ncl_logic; z : out ncl_logic ); end entity;
architecture dims of ncl_xor2 is signal m11,m10,m01,m00 : std_logic; begin
  m11<=th22(a.L,b.L); m10<=th22(a.L,b.H); m01<=th22(a.H,b.L); m00<=th22(a.H,b.H);
  z.L <= m10 or m01;   z.H <= m11 or m00;
end architecture dims;

-- ncl_xnor2 : Z = NOT(a XOR b)  -- XOR with rails swapped
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_xnor2 is port ( a, b : in ncl_logic; z : out ncl_logic ); end entity;
architecture dims of ncl_xnor2 is signal m11,m10,m01,m00 : std_logic; begin
  m11<=th22(a.L,b.L); m10<=th22(a.L,b.H); m01<=th22(a.H,b.L); m00<=th22(a.H,b.H);
  z.L <= m11 or m00;   z.H <= m10 or m01;
end architecture dims;

-- ncl_inv : Z = NOT a  -- a dual-rail inverter is a free RAIL SWAP (no gate,
-- no completion cost); the mapper emits it as wiring, not a cell.
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_inv is port ( a : in ncl_logic; z : out ncl_logic ); end entity;
architecture swap of ncl_inv is begin
  z.L <= a.H;   z.H <= a.L;
end architecture swap;

-- ncl_mux2 : Y = s ? b : a   (yosys $mux convention: S selects B).
-- 3-input DIMS: 8 TH33 minterms over (s,a,b), fully input-complete (waits for
-- ALL THREE inputs, incl. the unselected data input -- the conservative
-- correct-by-construction form; an early-completion MUX is a later optimization).
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_mux2 is port ( s, a, b : in ncl_logic; y : out ncl_logic ); end entity;
architecture dims of ncl_mux2 is
  -- m_sab : minterm for (s=.,a=.,b=.); rail .L = value 1, .H = value 0
  signal m010,m011,m101,m111 : std_logic;  -- y=1 minterms
  signal m000,m001,m100,m110 : std_logic;  -- y=0 minterms
begin
  -- y=1 : (s=0,a=1) or (s=1,b=1)
  m010 <= th33(s.H, a.L, b.H);   -- s0 a1 b0 -> y=a=1
  m011 <= th33(s.H, a.L, b.L);   -- s0 a1 b1 -> y=a=1
  m101 <= th33(s.L, a.H, b.L);   -- s1 a0 b1 -> y=b=1
  m111 <= th33(s.L, a.L, b.L);   -- s1 a1 b1 -> y=b=1
  -- y=0 : (s=0,a=0) or (s=1,b=0)
  m000 <= th33(s.H, a.H, b.H);   -- s0 a0 b0 -> y=a=0
  m001 <= th33(s.H, a.H, b.L);   -- s0 a0 b1 -> y=a=0
  m100 <= th33(s.L, a.H, b.H);   -- s1 a0 b0 -> y=b=0
  m110 <= th33(s.L, a.L, b.H);   -- s1 a1 b0 -> y=b=0
  y.L <= m010 or m011 or m101 or m111;
  y.H <= m000 or m001 or m100 or m110;
end architecture dims;

-- ===========================================================================
-- ncl_add4_behav — 4-bit adder, BEHAVIORAL dual-rail binding (lib/ncl ncl_add).
--   The sync-emulation-adjacent reference (decode/add/re-encode). Fast to
--   simulate; the EC reference the structural form is checked against.
-- ===========================================================================
library IEEE;
use IEEE.std_logic_1164.all;
library ncl;
use ncl.ncl.all;

entity ncl_add4_behav is
  port ( a, b : in ncl_logic_vector(3 downto 0); result : out ncl_logic_vector(3 downto 0) );
end entity ncl_add4_behav;

architecture ref of ncl_add4_behav is
begin
  result <= ncl_add(a, b);
end architecture ref;

-- ===========================================================================
-- ncl_add4_struct — 4-bit ripple adder, STRUCTURAL QDI (Fant full adder,
--   th23/th34w2 only).  The correct-by-construction form that lowers to
--   physical TH cells.  carry-in of bit 0 = constant DATA0 (spacer/reset carry
--   is the handshake layer's job).
-- ===========================================================================
library IEEE;
use IEEE.std_logic_1164.all;
library ncl;
use ncl.ncl.all;

entity ncl_add4_struct is
  port ( a, b : in ncl_logic_vector(3 downto 0); result : out ncl_logic_vector(3 downto 0) );
end entity ncl_add4_struct;

architecture ncl_struct of ncl_add4_struct is
begin
  process (a, b)
    variable at, af, bt, bf, cint, cinf, coutt, coutf, st, sf : std_logic;
    variable res : ncl_logic_vector(3 downto 0);
  begin
    cint := '0'; cinf := '1';            -- carry-in = DATA0 (value 0)
    for i in 0 to 3 loop
      at := a(i).L; af := a(i).H;
      bt := b(i).L; bf := b(i).H;
      coutt := th23(at, bt, cint);
      coutf := th23(af, bf, cinf);
      st    := th34w2(coutf, at, bt, cint);
      sf    := th34w2(coutt, af, bf, cinf);
      res(i) := (L => st, H => sf);
      cint := coutt; cinf := coutf;      -- ripple
    end loop;
    result <= res;
  end process;
end architecture ncl_struct;
