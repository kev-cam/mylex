-- This VHDL was converted from Verilog using the
-- Icarus Verilog VHDL Code Generator 13.0 (devel) (6029f3d-dirty)

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

-- Generated from Verilog module VX_pipe_register (libs/VX_pipe_register.sv:17)
--   DATAW = 2
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 1
entity VX_pipe_register is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    data_in : in logic3d_vector(1 downto 0);
    data_out : out logic3d_vector(1 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_register : entity is "libs/VX_pipe_register.sv:17";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_register : entity is "DATAW=2 DEPTH=1 INIT_VALUE=0 RESETW=1";
end entity; 

-- Generated from Verilog module VX_pipe_register (libs/VX_pipe_register.sv:17)
--   DATAW = 2
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 1
architecture from_verilog of VX_pipe_register is
  signal pipe_sig : logic3d_vector(1 downto 0) := (others => L3D_X);  -- Declared at libs/VX_pipe_register.sv:37
begin
  process (all) is

  begin
    data_out <= pipe_sig(0 + 1 downto 0);
  end process;
  
  -- Generated from always process in g_partial_reset (libs/VX_pipe_register.sv:51) [+ merged same-edge always block(s): libs/VX_pipe_register.sv:63]
  process is
    variable i : logic3d_vector(31 downto 0);
    variable i_2 : logic3d_vector(31 downto 0);
    variable v_nba_pipe_sig : logic3d_vector(1 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_pipe_sig := pipe_sig;
    if rising_edge(clk) then
      if is_one(reset) then
        i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
        while l3d_lt_s(i, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) loop
          v_nba_pipe_sig(l3d_index((l3d_resize_s(i, 33) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0)) + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1), True)) := L3D_0;
          i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        end loop;
      else
        if is_one(enable) then
          v_nba_pipe_sig(1) := data_in(1);
          i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
          while l3d_lt_s(i, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) loop
            v_nba_pipe_sig(l3d_index((l3d_resize_s(i, 33) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0)) + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1), True)) := l3d_bit_read(pipe_sig, l3d_index((l3d_resize_s((i - logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)), 33) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0)) + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1), True));
            i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
          end loop;
        end if;
      end if;
    end if;
    if rising_edge(clk) then
      if is_one(enable) then
        v_nba_pipe_sig(0) := data_in(0);
        i_2 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        while l3d_lt_s(i_2, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) loop
          v_nba_pipe_sig(l3d_index(l3d_resize_s(i_2, 33) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0), True)) := l3d_bit_read(pipe_sig, l3d_index(l3d_resize_s((i_2 - logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)), 33) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0), True));
          i_2 := i_2 + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        end loop;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    pipe_sig <= v_nba_pipe_sig;
    wait on clk;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

-- Generated from Verilog module VX_pipe_buffer (libs/VX_pipe_buffer.sv:21)
--   DATAW = 1
--   DEPTH = 1
--   RESETW = 0
entity VX_pipe_buffer is
  port (
    clk : in logic3d;
    reset : in logic3d;
    valid_in : in logic3d;
    ready_in : out logic3d;
    data_in : in logic3d;
    data_out : out logic3d;
    ready_out : in logic3d;
    valid_out : out logic3d
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_buffer : entity is "libs/VX_pipe_buffer.sv:21";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_buffer : entity is "DATAW=1 DEPTH=1 RESETW=0";
end entity; 

-- Generated from Verilog module VX_pipe_buffer (libs/VX_pipe_buffer.sv:21)
--   DATAW = 1
--   DEPTH = 1
--   RESETW = 0
architecture from_verilog of VX_pipe_buffer is
  signal tmp_ivl_21 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:60
  signal tmp_ivl_23 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:60
  signal tmp_ivl_3 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:46
  signal tmp_ivl_7 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:47
  signal data : logic3d_vector(1 downto 0) := (others => L3D_X);  -- Declared at libs/VX_pipe_buffer.sv:44
  type ready_Type is array (1 downto 0) of logic3d;
  signal ready : ready_Type;  -- Declared at libs/VX_pipe_buffer.sv:43
  signal valid : logic3d_vector(1 downto 0) := (others => L3D_X);  -- Declared at libs/VX_pipe_buffer.sv:42
  signal tmp_ivl_2_i0 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:51
  signal tmp_ivl_3_i0 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:51
  signal tmp_ivl_8_i0 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:59
  signal tmp_ivl_9_i0 : logic3d := L3D_X;  -- Temporary created at libs/VX_pipe_buffer.sv:59
  signal LPM_q_ivl_11_i0 : logic3d_vector(1 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_13_i0 : logic3d_vector(1 downto 0) := (others => L3D_X);
  
  component VX_pipe_register is
    port (
      clk : in logic3d;
      reset : in logic3d;
      enable : in logic3d;
      data_in : in logic3d_vector(1 downto 0);
      data_out : out logic3d_vector(1 downto 0)
    );
  end component;
begin
  process (all) is

  begin
    ready_in <= ready(0);
  end process;
  process (all) is

  begin
    ready(1) <= ready_out;
  end process;
  
  sv_or_g_register_g_pipe_regs_0_ivl_5: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => ready(0),
      a => ready(1) & tmp_ivl_3_i0
    );
  
  -- Generated from instantiation at libs/VX_pipe_buffer.sv:55
  pipe_register_i0: entity work.VX_pipe_register
    port map (
      clk => clk,
      data_in => LPM_q_ivl_11_i0,
      data_out => LPM_d0_ivl_13_i0,
      enable => ready(0),
      reset => reset
    );
  
  comb_fused_0: process (LPM_d0_ivl_13_i0, data_in, valid_in) is
  begin
    tmp_ivl_3 := valid_in;
    tmp_ivl_7 := data_in;
    tmp_ivl_21 := LPM_d0_ivl_13_i0(1);
    tmp_ivl_23 := LPM_d0_ivl_13_i0(0);
    valid := tmp_ivl_21 & tmp_ivl_3;
    data := tmp_ivl_23 & tmp_ivl_7;
    valid_out := valid(1);
    tmp_ivl_2_i0 := valid(1);
    tmp_ivl_8_i0 := valid(0);
    data_out := data(1);
    tmp_ivl_9_i0 := data(0);
    tmp_ivl_3_i0 := l3d_not(tmp_ivl_2_i0);
    LPM_q_ivl_11_i0 := tmp_ivl_8_i0 & tmp_ivl_9_i0;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

-- Generated from Verilog module VX_elastic_buffer (libs/VX_elastic_buffer.sv:17)
--   DATAW = 1
--   LUTRAM = 0
--   OUT_REG = 0
--   SIZE = 1
entity VX_elastic_buffer is
  port (
    clk : in logic3d;
    reset : in logic3d;
    valid_in : in logic3d;
    ready_in : out logic3d;
    data_in : in logic3d;
    data_out : out logic3d;
    ready_out : in logic3d;
    valid_out : out logic3d
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_elastic_buffer : entity is "libs/VX_elastic_buffer.sv:17";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_elastic_buffer : entity is "DATAW=1 LUTRAM=0 OUT_REG=0 SIZE=1";
end entity; 

-- Generated from Verilog module VX_elastic_buffer (libs/VX_elastic_buffer.sv:17)
--   DATAW = 1
--   LUTRAM = 0
--   OUT_REG = 0
--   SIZE = 1
architecture from_verilog of VX_elastic_buffer is
  
  component VX_pipe_buffer is
    port (
      clk : in logic3d;
      reset : in logic3d;
      valid_in : in logic3d;
      ready_in : out logic3d;
      data_in : in logic3d;
      data_out : out logic3d;
      ready_out : in logic3d;
      valid_out : out logic3d
    );
  end component;
  signal data_out_Readable : logic3d := L3D_X;  -- Needed to connect outputs
  signal ready_in_Readable : logic3d := L3D_X;  -- Needed to connect outputs
  signal valid_out_Readable : logic3d := L3D_X;  -- Needed to connect outputs
begin
  process (all) is

  begin
    data_out <= data_out_Readable;
  end process;
  process (all) is

  begin
    ready_in <= ready_in_Readable;
  end process;
  process (all) is

  begin
    valid_out <= valid_out_Readable;
  end process;
  
  -- Generated from instantiation at libs/VX_elastic_buffer.sv:48
  pipe_buffer: entity work.VX_pipe_buffer
    port map (
      clk => clk,
      data_in => data_in,
      data_out => data_out_Readable,
      ready_in => ready_in_Readable,
      ready_out => ready_out,
      reset => reset,
      valid_in => valid_in,
      valid_out => valid_out_Readable
    );
end architecture;

