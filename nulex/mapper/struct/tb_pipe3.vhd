-- Self-timed testbench for the 3-stage QDI pipeline (map_ncl_struct --reg qdi):
-- an always-ready consumer (ki_in = NOT ko_out), a 4-phase producer paced by the
-- input completion ko_in, and a checker that verifies each emitted DATA in order.
library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity tb_pipe3 is end entity;
architecture t of tb_pipe3 is
  signal d, q : ncl_logic_vector(3 downto 0);
  signal ki_in, ko_out, ko_in, clk : std_logic := '0';
  type ivec is array (natural range <>) of std_logic_vector(3 downto 0);
  constant seq : ivec := (x"1", x"2", x"4", x"8", x"F", x"3");
  signal done : boolean := false;
begin
  dut : entity work.pipe3 port map (clk=>clk, d=>d, ki_in=>ki_in, q=>q, ko_out=>ko_out, ko_in=>ko_in);
  ki_in <= not ko_out;                                     -- always-ready output consumer
  producer : process begin
    d <= (others => NCL_NULL);
    for i in seq'range loop
      wait until ko_in = '0';                              -- input stage empty -> present DATA
      d <= ncl_encode(seq(i));
      wait until ko_in = '1';                              -- captured -> present spacer NULL
      d <= (others => NCL_NULL);
    end loop;
    wait;
  end process;
  checker : process
    variable errs : integer := 0;
  begin
    for i in seq'range loop
      wait until ko_out = '1';                             -- a DATA word emerged
      if ncl_decode(q) /= seq(i) then errs := errs + 1;
        report "out(" & integer'image(i) & ") got " & to_hstring(ncl_decode(q))
             & " exp " & to_hstring(seq(i)) severity warning; end if;
      wait until ko_out = '0';                             -- its NULL spacer
    end loop;
    if errs = 0 then report "PIPE3 QDI: PASS (" & integer'image(seq'length)
        & " values through 3 async stages, self-timed)" severity note;
    else report "PIPE3 QDI: FAIL" severity failure; end if;
    done <= true; wait;
  end process;
  watchdog : process begin wait for 100 us; assert done report "WATCHDOG: pipeline deadlock" severity failure; wait; end process;
end architecture t;
