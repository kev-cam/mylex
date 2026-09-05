-- Tier B census, the last module: VX_dp_ram `mem-usage` -- tgt-vhdl's
-- NBA-shadow memory idiom on a 2-word RAM: the clocked process pre-copies
-- the whole array into v_nba_<ram>, writes one word under `if write`,
-- commits the whole array back after the delta guard; a comb process reads
-- a word through a concatenated address (`"00" & raddr`).
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r21_dpram is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r21_dpram is
  signal tmp_ivl_0 : logic3d_vector(50 downto 0) := (others => L3D_X);
  signal tmp_ivl_2 : logic3d_vector(2 downto 0) := (others => L3D_X);
  signal tmp_ivl_5 : logic3d_vector(1 downto 0) := (others => L3D_X);
  type ram_Type is array (1 downto 0) of logic3d_vector(50 downto 0);
  signal ram : ram_Type := (others => (others => L3D_0));
  signal rdata : logic3d_vector(50 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
  signal write : logic3d := L3D_X;
  signal waddr : logic3d_vector(0 downto 0) := (others => L3D_X);
  signal raddr : logic3d_vector(0 downto 0) := (others => L3D_X);
  signal wdata : logic3d_vector(50 downto 0) := (others => L3D_X);
begin
  y <= yr;
  write <= op(0);
  waddr <= op(1 downto 1);
  raddr <= op(2 downto 2);
  wdata <= a(18 downto 0) & b;
  process is
    variable v_nba_ram : ram_Type;
    variable nba_init_run : Boolean := True;
  begin
    v_nba_ram := ram;
    if rising_edge(clk) then
      if is_one(write) then
        v_nba_ram(To_Integer(waddr)) := wdata;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    ram <= v_nba_ram;
    wait on clk;
  end process;
  comb_fused_0: process (raddr, ram) is
  begin
    tmp_ivl_5 := logic3d_vector'(L3D_0, L3D_0);
    tmp_ivl_2 := tmp_ivl_5 & raddr;
    tmp_ivl_0 := ram(To_Integer(tmp_ivl_2));
    rdata := tmp_ivl_0;
  end process;
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        yr <= (others => L3D_0);
      else
        yr <= rdata(31 downto 0) xor (rdata(50 downto 32) & a(12 downto 0));
      end if;
    end if;
    wait on clk;
  end process;
end architecture;
