-- nulex/lib/ncl_reg_desync.vhd — DESYNCHRONIZATION register for FEEDBACK/cyclic logic.
--
-- Pure QDI 4-phase can't hold state around a feedback loop: a self-loop register
-- can't return-to-NULL without losing its value, and a hysteretic (QDI) datapath
-- can't RTZ while a persistent-DATA state input is held. Desynchronization is the
-- standard answer: a stateless (comb) datapath that returns to NULL, and a register
-- captured by a LOCAL self-timed clock derived from completion detection through a
-- MATCHED DELAY (bundled-data) so the combinational output has settled before capture
-- (raw completion can pulse on a transient-but-complete value while a stateless net
-- settles). One capture per DATA token; the feedback recompute after capture is not
-- re-latched because en does not re-edge until the next NULL->DATA cycle.
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity ncl_reg_desync is
  generic ( N     : positive := 1;
            TCOMB : time := 1 ns );        -- matched delay >= worst-case datapath settling
  port ( d : in  ncl_logic_vector(N-1 downto 0);
         q : out ncl_logic_vector(N-1 downto 0);
         done : out std_logic );            -- = en, the local self-timed clock
end entity ncl_reg_desync;

architecture desync of ncl_reg_desync is
  signal en : std_logic := '0';
  signal qi : ncl_logic_vector(N-1 downto 0) := (others => NCL_DATA0);
begin
  en <= ncl_complete(d) after TCOMB;        -- bundled-data local clock (settled completion)
  process (en) begin
    if rising_edge(en) then qi <= d; end if;  -- capture the settled next-state, once per token
  end process;
  q <= qi; done <= en;
end architecture desync;
