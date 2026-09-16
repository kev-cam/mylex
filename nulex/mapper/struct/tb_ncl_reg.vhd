library IEEE; use IEEE.std_logic_1164.all; library ncl; use ncl.ncl.all;
entity tb_ncl_reg is end entity;
architecture t of tb_ncl_reg is
  constant N : positive := 4;
  signal d, q : ncl_logic_vector(N-1 downto 0);
  signal ki, ko : std_logic;
begin
  dut : entity work.ncl_reg generic map (N => N) port map (d => d, ki => ki, q => q, ko => ko);
  process
    variable errs : integer := 0;
    procedure step(val : std_logic_vector(N-1 downto 0)) is
    begin
      d <= ncl_encode(val); ki <= '1'; wait for 10 ns;      -- present DATA, request data
      if ko /= '1' then errs := errs + 1; report "ko not set" severity warning; end if;
      if ncl_decode(q) /= val then errs := errs + 1;
        report "q mismatch: got " & to_hstring(ncl_decode(q)) severity warning; end if;
      d <= (others => NCL_NULL); ki <= '0'; wait for 10 ns;  -- present NULL, request null
      if ko /= '0' then errs := errs + 1; report "ko not cleared" severity warning; end if;
    end procedure;
  begin
    d <= (others => NCL_NULL); ki <= '0'; wait for 10 ns;    -- reset
    step("0000"); step("1010"); step("1111"); step("0110"); step("1001");
    if errs = 0 then report "NCL_REG QDI: PASS (4-phase capture + completion)" severity note;
    else report "NCL_REG QDI: FAIL" severity failure; end if;
    wait;
  end process;
end architecture t;
