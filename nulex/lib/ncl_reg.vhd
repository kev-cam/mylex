-- nulex/lib/ncl_reg.vhd — STRUCTURAL QDI NCL register (no clock; 4-phase RTZ).
--
-- The true delay-insensitive register the sync-emulation ncl_dff stood in for.
-- Built ONLY from TH cells (th_cells.vhd), correct-by-construction:
--   * per bit, each rail is a TH22 C-element gated by the request ki:
--       q.rail = TH22(d.rail, ki)   -- captures DATA when ki=1 & d arrives;
--       holds (hysteresis) until BOTH go low, i.e. d=NULL and ki=0 -> q=NULL.
--   * completion detection: per bit cd = TH12(q.L,q.H) (bit is DATA), then an
--     n-of-n C-element chain ko = TH22-chain(cd...) asserts only when ALL bits
--     are DATA and deasserts only when ALL are NULL (the DI completion tree).
-- Handshake: ki is the downstream request (1=give data, 0=give null); ko is the
-- completion out. In a pipeline, stage N's ki = NOT(stage N+1's ko).
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_reg is
  generic ( N : positive := 1 );
  port ( d  : in  ncl_logic_vector(N-1 downto 0);
         ki : in  std_logic;
         q  : out ncl_logic_vector(N-1 downto 0);
         ko : out std_logic );
end entity ncl_reg;

architecture qdi of ncl_reg is
  signal ql, qh, cd, acc : std_logic_vector(N-1 downto 0);
begin
  bits : for i in 0 to N-1 generate
    ul  : entity work.th22(qdi)  port map (a => d(i).L, b => ki,     y => ql(i));
    uh  : entity work.th22(qdi)  port map (a => d(i).H, b => ki,     y => qh(i));
    ucd : entity work.th12(comb) port map (a => ql(i), b => qh(i),   y => cd(i));
    q(i).L <= ql(i);
    q(i).H <= qh(i);
  end generate;
  acc(0) <= cd(0);
  tree : for i in 1 to N-1 generate
    ut : entity work.th22(qdi) port map (a => acc(i-1), b => cd(i), y => acc(i));
  end generate;
  ko <= acc(N-1);
end architecture qdi;
