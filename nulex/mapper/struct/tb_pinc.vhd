library IEEE; use IEEE.std_logic_1164.all; use IEEE.numeric_std.all; library ncl; use ncl.ncl.all;
entity tb_pinc is end entity;
architecture t of tb_pinc is
  signal d, q : ncl_logic_vector(3 downto 0);
  signal ki_in, ko_out, ko_in, clk : std_logic := '0';
  type ivec is array (natural range <>) of std_logic_vector(3 downto 0);
  constant seq : ivec := (x"0", x"5", x"F", x"A", x"7");
  signal done : boolean := false;
begin
  dut : entity work.pinc port map (clk=>clk, d=>d, ki_in=>ki_in, q=>q, ko_out=>ko_out, ko_in=>ko_in);
  ki_in <= not ko_out;
  producer : process begin
    d <= (others => NCL_NULL);
    for i in seq'range loop
      wait until ko_in = '0'; d <= ncl_encode(seq(i));
      wait until ko_in = '1'; d <= (others => NCL_NULL);
    end loop; wait;
  end process;
  checker : process
    variable errs : integer := 0; variable exp : std_logic_vector(3 downto 0);
  begin
    for i in seq'range loop
      wait until ko_out = '1';
      exp := std_logic_vector(unsigned(seq(i)) + 1);       -- pipeline computes d+1
      if ncl_decode(q) /= exp then errs := errs + 1;
        report "out("&integer'image(i)&") got "&to_hstring(ncl_decode(q))&" exp "&to_hstring(exp) severity warning; end if;
      wait until ko_out = '0';
    end loop;
    if errs = 0 then report "PINC QDI: PASS (2-stage pipeline, q = d+1, self-timed)" severity note;
    else report "PINC QDI: FAIL" severity failure; end if;
    done <= true; wait;
  end process;
  watchdog : process begin wait for 100 us; assert done report "deadlock" severity failure; wait; end process;
end architecture t;
