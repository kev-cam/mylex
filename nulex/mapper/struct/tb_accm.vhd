library IEEE; use IEEE.std_logic_1164.all; use IEEE.numeric_std.all; library ncl; use ncl.ncl.all;
entity tb_accm is end entity;
architecture t of tb_accm is
  signal din, q : ncl_logic_vector(3 downto 0);
  signal done, clk : std_logic := '0';
  type ivec is array (natural range <>) of integer;
  constant seq : ivec := (3, 5, 1, 8, 4, 15, 2);
  signal fin : boolean := false;
begin
  dut : entity work.accm port map (clk => clk, din => din, q => q, done => done);
  process
    variable acc : integer := 0; variable errs : integer := 0;
  begin
    din <= (others => NCL_NULL); wait for 20 ns;
    for i in seq'range loop
      din <= ncl_encode(std_logic_vector(to_unsigned(seq(i), 4)));
      wait until done = '1'; wait for 1 ns;
      din <= (others => NCL_NULL);
      wait until done = '0'; wait for 1 ns;
      acc := (acc + seq(i)) mod 16;
      if to_integer(unsigned(ncl_decode(q))) /= acc then errs := errs + 1;
        report "+" & integer'image(seq(i)) & " -> q=" & integer'image(to_integer(unsigned(ncl_decode(q))))
             & " exp " & integer'image(acc) severity warning; end if;
    end loop;
    if errs = 0 then report "ACCM DESYNC (emitted by map_ncl_struct --reg desync): PASS" severity note;
    else report "ACCM DESYNC: FAIL" severity failure; end if;
    fin <= true; wait;
  end process;
  wd : process begin wait for 50 us; assert fin report "deadlock" severity failure; wait; end process;
end architecture t;
