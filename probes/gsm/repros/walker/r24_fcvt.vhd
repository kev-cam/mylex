library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

-- Generated from Verilog module VX_find_first (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1314)
--   DATAW = 5
--   LOGN = 5
--   N = 32
--   REVERSE = 1
--   TL = 31
--   TN = 63
entity VX_find_first is
  port (
    data_in : in logic3d_vector(159 downto 0);
    valid_in : in logic3d_vector(31 downto 0);
    data_out : out logic3d_vector(4 downto 0);
    valid_out : out logic3d
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_find_first : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1314";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_find_first : entity is "DATAW=5 LOGN=5 N=32 REVERSE=1 TL=31 TN=63";
end entity; 

-- Generated from Verilog module VX_find_first (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1314)
--   DATAW = 5
--   LOGN = 5
--   N = 32
--   REVERSE = 1
--   TL = 31
--   TN = 63
architecture from_verilog of VX_find_first is
  type d_n_Type is array (62 downto 0) of logic3d_vector(4 downto 0);
  signal d_n : d_n_Type := (others => (others => L3D_X));  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1331
  type s_n_Type is array (62 downto 0) of logic3d;
  signal s_n : s_n_Type;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1330
begin
  process (all) is

  begin
    valid_out <= s_n(0);
  end process;
  process (all) is

  begin
    data_out <= d_n(0);
  end process;
  process (all) is

  begin
    s_n(31) <= valid_in(31);
  end process;
  process (all) is

  begin
    d_n(31) <= data_in(155 + 4 downto 155);
  end process;
  process (all) is

  begin
    s_n(32) <= valid_in(30);
  end process;
  process (all) is

  begin
    d_n(32) <= data_in(150 + 4 downto 150);
  end process;
  process (all) is

  begin
    s_n(33) <= valid_in(29);
  end process;
  process (all) is

  begin
    d_n(33) <= data_in(145 + 4 downto 145);
  end process;
  process (all) is

  begin
    s_n(34) <= valid_in(28);
  end process;
  process (all) is

  begin
    d_n(34) <= data_in(140 + 4 downto 140);
  end process;
  process (all) is

  begin
    s_n(35) <= valid_in(27);
  end process;
  process (all) is

  begin
    d_n(35) <= data_in(135 + 4 downto 135);
  end process;
  process (all) is

  begin
    s_n(36) <= valid_in(26);
  end process;
  process (all) is

  begin
    d_n(36) <= data_in(130 + 4 downto 130);
  end process;
  process (all) is

  begin
    s_n(37) <= valid_in(25);
  end process;
  process (all) is

  begin
    d_n(37) <= data_in(125 + 4 downto 125);
  end process;
  process (all) is

  begin
    s_n(38) <= valid_in(24);
  end process;
  process (all) is

  begin
    d_n(38) <= data_in(120 + 4 downto 120);
  end process;
  process (all) is

  begin
    s_n(39) <= valid_in(23);
  end process;
  process (all) is

  begin
    d_n(39) <= data_in(115 + 4 downto 115);
  end process;
  process (all) is

  begin
    s_n(40) <= valid_in(22);
  end process;
  process (all) is

  begin
    d_n(40) <= data_in(110 + 4 downto 110);
  end process;
  process (all) is

  begin
    s_n(41) <= valid_in(21);
  end process;
  process (all) is

  begin
    d_n(41) <= data_in(105 + 4 downto 105);
  end process;
  process (all) is

  begin
    s_n(42) <= valid_in(20);
  end process;
  process (all) is

  begin
    d_n(42) <= data_in(100 + 4 downto 100);
  end process;
  process (all) is

  begin
    s_n(43) <= valid_in(19);
  end process;
  process (all) is

  begin
    d_n(43) <= data_in(95 + 4 downto 95);
  end process;
  process (all) is

  begin
    s_n(44) <= valid_in(18);
  end process;
  process (all) is

  begin
    d_n(44) <= data_in(90 + 4 downto 90);
  end process;
  process (all) is

  begin
    s_n(45) <= valid_in(17);
  end process;
  process (all) is

  begin
    d_n(45) <= data_in(85 + 4 downto 85);
  end process;
  process (all) is

  begin
    s_n(46) <= valid_in(16);
  end process;
  process (all) is

  begin
    d_n(46) <= data_in(80 + 4 downto 80);
  end process;
  process (all) is

  begin
    s_n(47) <= valid_in(15);
  end process;
  process (all) is

  begin
    d_n(47) <= data_in(75 + 4 downto 75);
  end process;
  process (all) is

  begin
    s_n(48) <= valid_in(14);
  end process;
  process (all) is

  begin
    d_n(48) <= data_in(70 + 4 downto 70);
  end process;
  process (all) is

  begin
    s_n(49) <= valid_in(13);
  end process;
  process (all) is

  begin
    d_n(49) <= data_in(65 + 4 downto 65);
  end process;
  process (all) is

  begin
    s_n(50) <= valid_in(12);
  end process;
  process (all) is

  begin
    d_n(50) <= data_in(60 + 4 downto 60);
  end process;
  process (all) is

  begin
    s_n(51) <= valid_in(11);
  end process;
  process (all) is

  begin
    d_n(51) <= data_in(55 + 4 downto 55);
  end process;
  process (all) is

  begin
    s_n(52) <= valid_in(10);
  end process;
  process (all) is

  begin
    d_n(52) <= data_in(50 + 4 downto 50);
  end process;
  process (all) is

  begin
    s_n(53) <= valid_in(9);
  end process;
  process (all) is

  begin
    d_n(53) <= data_in(45 + 4 downto 45);
  end process;
  process (all) is

  begin
    s_n(54) <= valid_in(8);
  end process;
  process (all) is

  begin
    d_n(54) <= data_in(40 + 4 downto 40);
  end process;
  process (all) is

  begin
    s_n(55) <= valid_in(7);
  end process;
  process (all) is

  begin
    d_n(55) <= data_in(35 + 4 downto 35);
  end process;
  process (all) is

  begin
    s_n(56) <= valid_in(6);
  end process;
  process (all) is

  begin
    d_n(56) <= data_in(30 + 4 downto 30);
  end process;
  process (all) is

  begin
    s_n(57) <= valid_in(5);
  end process;
  process (all) is

  begin
    d_n(57) <= data_in(25 + 4 downto 25);
  end process;
  process (all) is

  begin
    s_n(58) <= valid_in(4);
  end process;
  process (all) is

  begin
    d_n(58) <= data_in(20 + 4 downto 20);
  end process;
  process (all) is

  begin
    s_n(59) <= valid_in(3);
  end process;
  process (all) is

  begin
    d_n(59) <= data_in(15 + 4 downto 15);
  end process;
  process (all) is

  begin
    s_n(60) <= valid_in(2);
  end process;
  process (all) is

  begin
    d_n(60) <= data_in(10 + 4 downto 10);
  end process;
  process (all) is

  begin
    s_n(61) <= valid_in(1);
  end process;
  process (all) is

  begin
    d_n(61) <= data_in(5 + 4 downto 5);
  end process;
  process (all) is

  begin
    s_n(62) <= valid_in(0);
  end process;
  process (all) is

  begin
    d_n(62) <= data_in(0 + 4 downto 0);
  end process;
  
  sv_or_g_scan_0_g_i_0_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(0),
      a => s_n(2) & s_n(1)
    );
  process (all) is

  begin
    if is_one(s_n(1)) then
      d_n(0) <= d_n(1);
    else
      d_n(0) <= d_n(2);
    end if;
  end process;
  
  sv_or_g_scan_1_g_i_0_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(1),
      a => s_n(4) & s_n(3)
    );
  process (all) is

  begin
    if is_one(s_n(3)) then
      d_n(1) <= d_n(3);
    else
      d_n(1) <= d_n(4);
    end if;
  end process;
  
  sv_or_g_scan_1_g_i_1_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(2),
      a => s_n(6) & s_n(5)
    );
  process (all) is

  begin
    if is_one(s_n(5)) then
      d_n(2) <= d_n(5);
    else
      d_n(2) <= d_n(6);
    end if;
  end process;
  
  sv_or_g_scan_2_g_i_0_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(3),
      a => s_n(8) & s_n(7)
    );
  process (all) is

  begin
    if is_one(s_n(7)) then
      d_n(3) <= d_n(7);
    else
      d_n(3) <= d_n(8);
    end if;
  end process;
  
  sv_or_g_scan_2_g_i_1_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(4),
      a => s_n(10) & s_n(9)
    );
  process (all) is

  begin
    if is_one(s_n(9)) then
      d_n(4) <= d_n(9);
    else
      d_n(4) <= d_n(10);
    end if;
  end process;
  
  sv_or_g_scan_2_g_i_2_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(5),
      a => s_n(12) & s_n(11)
    );
  process (all) is

  begin
    if is_one(s_n(11)) then
      d_n(5) <= d_n(11);
    else
      d_n(5) <= d_n(12);
    end if;
  end process;
  
  sv_or_g_scan_2_g_i_3_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(6),
      a => s_n(14) & s_n(13)
    );
  process (all) is

  begin
    if is_one(s_n(13)) then
      d_n(6) <= d_n(13);
    else
      d_n(6) <= d_n(14);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_0_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(7),
      a => s_n(16) & s_n(15)
    );
  process (all) is

  begin
    if is_one(s_n(15)) then
      d_n(7) <= d_n(15);
    else
      d_n(7) <= d_n(16);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_1_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(8),
      a => s_n(18) & s_n(17)
    );
  process (all) is

  begin
    if is_one(s_n(17)) then
      d_n(8) <= d_n(17);
    else
      d_n(8) <= d_n(18);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_2_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(9),
      a => s_n(20) & s_n(19)
    );
  process (all) is

  begin
    if is_one(s_n(19)) then
      d_n(9) <= d_n(19);
    else
      d_n(9) <= d_n(20);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_3_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(10),
      a => s_n(22) & s_n(21)
    );
  process (all) is

  begin
    if is_one(s_n(21)) then
      d_n(10) <= d_n(21);
    else
      d_n(10) <= d_n(22);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_4_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(11),
      a => s_n(24) & s_n(23)
    );
  process (all) is

  begin
    if is_one(s_n(23)) then
      d_n(11) <= d_n(23);
    else
      d_n(11) <= d_n(24);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_5_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(12),
      a => s_n(26) & s_n(25)
    );
  process (all) is

  begin
    if is_one(s_n(25)) then
      d_n(12) <= d_n(25);
    else
      d_n(12) <= d_n(26);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_6_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(13),
      a => s_n(28) & s_n(27)
    );
  process (all) is

  begin
    if is_one(s_n(27)) then
      d_n(13) <= d_n(27);
    else
      d_n(13) <= d_n(28);
    end if;
  end process;
  
  sv_or_g_scan_3_g_i_7_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(14),
      a => s_n(30) & s_n(29)
    );
  process (all) is

  begin
    if is_one(s_n(29)) then
      d_n(14) <= d_n(29);
    else
      d_n(14) <= d_n(30);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_0_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(15),
      a => s_n(32) & s_n(31)
    );
  process (all) is

  begin
    if is_one(s_n(31)) then
      d_n(15) <= d_n(31);
    else
      d_n(15) <= d_n(32);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_1_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(16),
      a => s_n(34) & s_n(33)
    );
  process (all) is

  begin
    if is_one(s_n(33)) then
      d_n(16) <= d_n(33);
    else
      d_n(16) <= d_n(34);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_2_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(17),
      a => s_n(36) & s_n(35)
    );
  process (all) is

  begin
    if is_one(s_n(35)) then
      d_n(17) <= d_n(35);
    else
      d_n(17) <= d_n(36);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_3_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(18),
      a => s_n(38) & s_n(37)
    );
  process (all) is

  begin
    if is_one(s_n(37)) then
      d_n(18) <= d_n(37);
    else
      d_n(18) <= d_n(38);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_4_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(19),
      a => s_n(40) & s_n(39)
    );
  process (all) is

  begin
    if is_one(s_n(39)) then
      d_n(19) <= d_n(39);
    else
      d_n(19) <= d_n(40);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_5_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(20),
      a => s_n(42) & s_n(41)
    );
  process (all) is

  begin
    if is_one(s_n(41)) then
      d_n(20) <= d_n(41);
    else
      d_n(20) <= d_n(42);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_6_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(21),
      a => s_n(44) & s_n(43)
    );
  process (all) is

  begin
    if is_one(s_n(43)) then
      d_n(21) <= d_n(43);
    else
      d_n(21) <= d_n(44);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_7_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(22),
      a => s_n(46) & s_n(45)
    );
  process (all) is

  begin
    if is_one(s_n(45)) then
      d_n(22) <= d_n(45);
    else
      d_n(22) <= d_n(46);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_8_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(23),
      a => s_n(48) & s_n(47)
    );
  process (all) is

  begin
    if is_one(s_n(47)) then
      d_n(23) <= d_n(47);
    else
      d_n(23) <= d_n(48);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_9_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(24),
      a => s_n(50) & s_n(49)
    );
  process (all) is

  begin
    if is_one(s_n(49)) then
      d_n(24) <= d_n(49);
    else
      d_n(24) <= d_n(50);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_10_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(25),
      a => s_n(52) & s_n(51)
    );
  process (all) is

  begin
    if is_one(s_n(51)) then
      d_n(25) <= d_n(51);
    else
      d_n(25) <= d_n(52);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_11_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(26),
      a => s_n(54) & s_n(53)
    );
  process (all) is

  begin
    if is_one(s_n(53)) then
      d_n(26) <= d_n(53);
    else
      d_n(26) <= d_n(54);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_12_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(27),
      a => s_n(56) & s_n(55)
    );
  process (all) is

  begin
    if is_one(s_n(55)) then
      d_n(27) <= d_n(55);
    else
      d_n(27) <= d_n(56);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_13_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(28),
      a => s_n(58) & s_n(57)
    );
  process (all) is

  begin
    if is_one(s_n(57)) then
      d_n(28) <= d_n(57);
    else
      d_n(28) <= d_n(58);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_14_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(29),
      a => s_n(60) & s_n(59)
    );
  process (all) is

  begin
    if is_one(s_n(59)) then
      d_n(29) <= d_n(59);
    else
      d_n(29) <= d_n(60);
    end if;
  end process;
  
  sv_or_g_scan_4_g_i_15_ivl_4: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => s_n(30),
      a => s_n(62) & s_n(61)
    );
  process (all) is

  begin
    if is_one(s_n(61)) then
      d_n(30) <= d_n(61);
    else
      d_n(30) <= d_n(62);
    end if;
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

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 37
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
entity VX_pipe_register8 is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    data_in : in logic3d_vector(36 downto 0);
    data_out : out logic3d_vector(36 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_register8 : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_register8 : entity is "DATAW=37 DEPTH=1 INIT_VALUE=0 RESETW=0";
end entity; 

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 37
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
architecture from_verilog of VX_pipe_register8 is
  signal pipe_sig_g_pipe : logic3d_vector(36 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3107
begin
  process (all) is

  begin
    data_out <= pipe_sig_g_pipe;
  end process;
  
  -- Generated from always process in g_no_reset (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3147)
  process is
    variable i : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Tmp_48 : logic3d_vector(36 downto 0);
    variable OOB_WriteV_Idx_48 : Integer;
    variable OOB_WriteV_Tmp_49 : logic3d_vector(36 downto 0);
    variable OOB_WriteV_Idx_49 : Integer;
    variable v_nba_pipe_sig_g_pipe : logic3d_vector(36 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_pipe_sig_g_pipe := pipe_sig_g_pipe;
    if rising_edge(clk) then
      if is_one(enable) then
        v_nba_pipe_sig_g_pipe := data_in;
        i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        while l3d_lt_s(i, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) loop
          OOB_WriteV_Tmp_49 := l3d_part_read(pipe_sig_g_pipe, l3d_index((i - logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1), True), 37);
          OOB_WriteV_Idx_49 := l3d_index(i * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1), True);
          if (OOB_WriteV_Idx_49 >= -36) and (OOB_WriteV_Idx_49 <= 36) then
            for OOB_P in 0 to 36 loop
              if ((OOB_WriteV_Idx_49 + OOB_P) >= 0) and ((OOB_WriteV_Idx_49 + OOB_P) <= 36) then
                v_nba_pipe_sig_g_pipe(OOB_WriteV_Idx_49 + OOB_P) := OOB_WriteV_Tmp_49(OOB_P);
              end if;
            end loop;
          end if;
          i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        end loop;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    pipe_sig_g_pipe <= v_nba_pipe_sig_g_pipe;
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

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 85
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
entity VX_pipe_register7 is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    data_in : in logic3d_vector(84 downto 0);
    data_out : out logic3d_vector(84 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_register7 : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_register7 : entity is "DATAW=85 DEPTH=1 INIT_VALUE=0 RESETW=0";
end entity; 

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 85
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
architecture from_verilog of VX_pipe_register7 is
  signal pipe_sig_g_pipe : logic3d_vector(84 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3107
begin
  process (all) is

  begin
    data_out <= pipe_sig_g_pipe;
  end process;
  
  -- Generated from always process in g_no_reset (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3147)
  process is
    variable i : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Tmp_46 : logic3d_vector(84 downto 0);
    variable OOB_WriteV_Idx_46 : Integer;
    variable OOB_WriteV_Tmp_47 : logic3d_vector(84 downto 0);
    variable OOB_WriteV_Idx_47 : Integer;
    variable v_nba_pipe_sig_g_pipe : logic3d_vector(84 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_pipe_sig_g_pipe := pipe_sig_g_pipe;
    if rising_edge(clk) then
      if is_one(enable) then
        v_nba_pipe_sig_g_pipe := data_in;
        i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        while i < logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1) loop
          OOB_WriteV_Tmp_47 := l3d_part_read(pipe_sig_g_pipe, l3d_index((l3d_resize_s(i, 37) - logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1, L3D_0, L3D_1, L3D_0, L3D_1), True), 85);
          OOB_WriteV_Idx_47 := l3d_index(l3d_resize_s(i, 37) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1, L3D_0, L3D_1, L3D_0, L3D_1), True);
          if (OOB_WriteV_Idx_47 >= -84) and (OOB_WriteV_Idx_47 <= 84) then
            for OOB_P in 0 to 84 loop
              if ((OOB_WriteV_Idx_47 + OOB_P) >= 0) and ((OOB_WriteV_Idx_47 + OOB_P) <= 84) then
                v_nba_pipe_sig_g_pipe(OOB_WriteV_Idx_47 + OOB_P) := OOB_WriteV_Tmp_47(OOB_P);
              end if;
            end loop;
          end if;
          i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        end loop;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    pipe_sig_g_pipe <= v_nba_pipe_sig_g_pipe;
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

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 75
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
entity VX_pipe_register6 is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    data_in : in logic3d_vector(74 downto 0);
    data_out : out logic3d_vector(74 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_register6 : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_register6 : entity is "DATAW=75 DEPTH=1 INIT_VALUE=0 RESETW=0";
end entity; 

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 75
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
architecture from_verilog of VX_pipe_register6 is
  signal pipe_sig_g_pipe : logic3d_vector(74 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3107
begin
  process (all) is

  begin
    data_out <= pipe_sig_g_pipe;
  end process;
  
  -- Generated from always process in g_no_reset (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3147)
  process is
    variable i : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Tmp_44 : logic3d_vector(74 downto 0);
    variable OOB_WriteV_Idx_44 : Integer;
    variable OOB_WriteV_Tmp_45 : logic3d_vector(74 downto 0);
    variable OOB_WriteV_Idx_45 : Integer;
    variable v_nba_pipe_sig_g_pipe : logic3d_vector(74 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_pipe_sig_g_pipe := pipe_sig_g_pipe;
    if rising_edge(clk) then
      if is_one(enable) then
        v_nba_pipe_sig_g_pipe := data_in;
        i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        while i < logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1) loop
          OOB_WriteV_Tmp_45 := l3d_part_read(pipe_sig_g_pipe, l3d_index((l3d_resize_s(i, 67) - logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1, L3D_1), True), 75);
          OOB_WriteV_Idx_45 := l3d_index(l3d_resize_s(i, 67) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1, L3D_1), True);
          if (OOB_WriteV_Idx_45 >= -74) and (OOB_WriteV_Idx_45 <= 74) then
            for OOB_P in 0 to 74 loop
              if ((OOB_WriteV_Idx_45 + OOB_P) >= 0) and ((OOB_WriteV_Idx_45 + OOB_P) <= 74) then
                v_nba_pipe_sig_g_pipe(OOB_WriteV_Idx_45 + OOB_P) := OOB_WriteV_Tmp_45(OOB_P);
              end if;
            end loop;
          end if;
          i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        end loop;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    pipe_sig_g_pipe <= v_nba_pipe_sig_g_pipe;
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

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 68
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
entity VX_pipe_register5 is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    data_in : in logic3d_vector(67 downto 0);
    data_out : out logic3d_vector(67 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_register5 : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_register5 : entity is "DATAW=68 DEPTH=1 INIT_VALUE=0 RESETW=0";
end entity; 

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 68
--   DEPTH = 1
--   INIT_VALUE = 0
--   RESETW = 0
architecture from_verilog of VX_pipe_register5 is
  signal pipe_sig_g_pipe : logic3d_vector(67 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3107
begin
  process (all) is

  begin
    data_out <= pipe_sig_g_pipe;
  end process;
  
  -- Generated from always process in g_no_reset (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3147)
  process is
    variable i : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Tmp_42 : logic3d_vector(67 downto 0);
    variable OOB_WriteV_Idx_42 : Integer;
    variable OOB_WriteV_Tmp_43 : logic3d_vector(67 downto 0);
    variable OOB_WriteV_Idx_43 : Integer;
    variable v_nba_pipe_sig_g_pipe : logic3d_vector(67 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_pipe_sig_g_pipe := pipe_sig_g_pipe;
    if rising_edge(clk) then
      if is_one(enable) then
        v_nba_pipe_sig_g_pipe := data_in;
        i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        while i < logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1) loop
          OOB_WriteV_Tmp_43 := l3d_part_read(pipe_sig_g_pipe, l3d_index((l3d_resize_s(i, 36) - logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0), True), 68);
          OOB_WriteV_Idx_43 := l3d_index(l3d_resize_s(i, 36) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0), True);
          if (OOB_WriteV_Idx_43 >= -67) and (OOB_WriteV_Idx_43 <= 67) then
            for OOB_P in 0 to 67 loop
              if ((OOB_WriteV_Idx_43 + OOB_P) >= 0) and ((OOB_WriteV_Idx_43 + OOB_P) <= 67) then
                v_nba_pipe_sig_g_pipe(OOB_WriteV_Idx_43 + OOB_P) := OOB_WriteV_Tmp_43(OOB_P);
              end if;
            end loop;
          end if;
          i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
        end loop;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    pipe_sig_g_pipe <= v_nba_pipe_sig_g_pipe;
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

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 62
--   DEPTH = 0
--   INIT_VALUE = 0
--   RESETW = 0
entity VX_pipe_register4 is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    data_in : in logic3d_vector(61 downto 0);
    data_out : out logic3d_vector(61 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_pipe_register4 : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_pipe_register4 : entity is "DATAW=62 DEPTH=0 INIT_VALUE=0 RESETW=0";
end entity; 

-- Generated from Verilog module VX_pipe_register (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:3086)
--   DATAW = 62
--   DEPTH = 0
--   INIT_VALUE = 0
--   RESETW = 0
architecture from_verilog of VX_pipe_register4 is
begin
  process (all) is

  begin
    data_out <= data_in;
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

-- Generated from Verilog module VX_lzc (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1659)
--   LOGN = 5
--   N = 32
--   REVERSE = 0
entity VX_lzc is
  port (
    data_in : in logic3d_vector(31 downto 0);
    data_out : out logic3d_vector(4 downto 0);
    valid_out : out logic3d
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_lzc : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1659";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_lzc : entity is "LOGN=5 N=32 REVERSE=0";
end entity; 

-- Generated from Verilog module VX_lzc (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1659)
--   LOGN = 5
--   N = 32
--   REVERSE = 0
architecture from_verilog of VX_lzc is
  impure function sv2v_cast_0FCEB_signed (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector;
  
  signal indices_g_lzc : logic3d_vector(159 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1680
  signal tmp_ivl_0_g_lzc_g_indices_0 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_0 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_1 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_1 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_2 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_2 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_3 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_3 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_4 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_4 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_5 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_5 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_6 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_6 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_7 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_7 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_8 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_8 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_9 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_9 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_10 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_10 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_11 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_11 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_12 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_12 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_13 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_13 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_14 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_14 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_15 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_15 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_16 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_16 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_17 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_17 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_18 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_18 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_19 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_19 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_20 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_20 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_21 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_21 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_22 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_22 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_23 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_23 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_24 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_24 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_25 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_25 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_26 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_26 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_27 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_27 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_28 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_28 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_29 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_29 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_30 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_30 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_0_g_lzc_g_indices_31 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  signal tmp_ivl_3_g_lzc_g_indices_31 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1684
  
  component VX_find_first is
    port (
      data_in : in logic3d_vector(159 downto 0);
      valid_in : in logic3d_vector(31 downto 0);
      data_out : out logic3d_vector(4 downto 0);
      valid_out : out logic3d
    );
  end component;
  signal data_out_Readable : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Needed to connect outputs
  signal valid_out_Readable : logic3d := L3D_X;  -- Needed to connect outputs
  
  -- Generated from function sv2v_cast_0FCEB_signed at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1670
  impure function sv2v_cast_0FCEB_signed (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_0FCEB_signed_Result : logic3d_vector(4 downto 0);
  begin
    sv2v_cast_0FCEB_signed_Result := inp;
    return sv2v_cast_0FCEB_signed_Result;
  end function;
begin
  process (all) is

  begin
    indices_g_lzc <= tmp_ivl_3_g_lzc_g_indices_31 & tmp_ivl_3_g_lzc_g_indices_30 & tmp_ivl_3_g_lzc_g_indices_29 & tmp_ivl_3_g_lzc_g_indices_28 & tmp_ivl_3_g_lzc_g_indices_27 & tmp_ivl_3_g_lzc_g_indices_26 & tmp_ivl_3_g_lzc_g_indices_25 & tmp_ivl_3_g_lzc_g_indices_24 & tmp_ivl_3_g_lzc_g_indices_23 & tmp_ivl_3_g_lzc_g_indices_22 & tmp_ivl_3_g_lzc_g_indices_21 & tmp_ivl_3_g_lzc_g_indices_20 & tmp_ivl_3_g_lzc_g_indices_19 & tmp_ivl_3_g_lzc_g_indices_18 & tmp_ivl_3_g_lzc_g_indices_17 & tmp_ivl_3_g_lzc_g_indices_16 & tmp_ivl_3_g_lzc_g_indices_15 & tmp_ivl_3_g_lzc_g_indices_14 & tmp_ivl_3_g_lzc_g_indices_13 & tmp_ivl_3_g_lzc_g_indices_12 & tmp_ivl_3_g_lzc_g_indices_11 & tmp_ivl_3_g_lzc_g_indices_10 & tmp_ivl_3_g_lzc_g_indices_9 & tmp_ivl_3_g_lzc_g_indices_8 & tmp_ivl_3_g_lzc_g_indices_7 & tmp_ivl_3_g_lzc_g_indices_6 & tmp_ivl_3_g_lzc_g_indices_5 & tmp_ivl_3_g_lzc_g_indices_4 & tmp_ivl_3_g_lzc_g_indices_3 & tmp_ivl_3_g_lzc_g_indices_2 & tmp_ivl_3_g_lzc_g_indices_1 & tmp_ivl_3_g_lzc_g_indices_0;
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_0 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_0);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_1 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_1);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_2 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_2);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_3 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_3);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_4 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_4);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_5 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_5);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_6 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_6);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_7 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_7);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_8 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_8);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_9 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_9);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_10 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_10);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_11 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_11);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_12 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_12);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_13 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_13);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_14 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_14);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_15 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_15);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_16 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_16);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_17 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_17);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_18 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_18);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_19 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_19);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_20 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_20);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_21 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_21);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_22 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_22);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_23 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_23);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_24 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_24);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_25 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_25);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_26 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_26);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_27 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_27);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_28 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_28);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_29 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_29);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_30 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_30);
  end process;
  process (all) is

  begin
    tmp_ivl_3_g_lzc_g_indices_31 <= sv2v_cast_0FCEB_signed(tmp_ivl_0_g_lzc_g_indices_31);
  end process;
  process (all) is

  begin
    data_out <= data_out_Readable;
  end process;
  process (all) is

  begin
    valid_out <= valid_out_Readable;
  end process;
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:1690
  find_first_g_lzc: entity work.VX_find_first
    port map (
      data_in => indices_g_lzc,
      data_out => data_out_Readable,
      valid_in => data_in,
      valid_out => valid_out_Readable
    );
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_0 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_1 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_2 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_3 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_4 <= logic3d_vector'(L3D_1, L3D_1, L3D_0, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_5 <= logic3d_vector'(L3D_1, L3D_1, L3D_0, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_6 <= logic3d_vector'(L3D_1, L3D_1, L3D_0, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_7 <= logic3d_vector'(L3D_1, L3D_1, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_8 <= logic3d_vector'(L3D_1, L3D_0, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_9 <= logic3d_vector'(L3D_1, L3D_0, L3D_1, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_10 <= logic3d_vector'(L3D_1, L3D_0, L3D_1, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_11 <= logic3d_vector'(L3D_1, L3D_0, L3D_1, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_12 <= logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_13 <= logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_14 <= logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_15 <= logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_16 <= logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_17 <= logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_18 <= logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_19 <= logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_20 <= logic3d_vector'(L3D_0, L3D_1, L3D_0, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_21 <= logic3d_vector'(L3D_0, L3D_1, L3D_0, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_22 <= logic3d_vector'(L3D_0, L3D_1, L3D_0, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_23 <= logic3d_vector'(L3D_0, L3D_1, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_24 <= logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_25 <= logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_26 <= logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_27 <= logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_28 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_29 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_1, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_30 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_0_g_lzc_g_indices_31 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
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

-- Generated from Verilog module VX_fp_rounding (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6520)
--   DAT_WIDTH = 32
--   VX_gpu_pkg_INST_FRM_RDN = 2
--   VX_gpu_pkg_INST_FRM_RMM = 4
--   VX_gpu_pkg_INST_FRM_RNE = 0
--   VX_gpu_pkg_INST_FRM_RTZ = 1
--   VX_gpu_pkg_INST_FRM_RUP = 3
entity VX_fp_rounding is
  port (
    abs_value_i : in logic3d_vector(31 downto 0);
    sign_i : in logic3d;
    round_sticky_bits_i : in logic3d_vector(1 downto 0);
    rnd_mode_i : in logic3d_vector(2 downto 0);
    effective_subtraction_i : in logic3d;
    abs_rounded_o : out logic3d_vector(31 downto 0);
    sign_o : out logic3d;
    exact_zero_o : buffer logic3d
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_fp_rounding : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6520";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_fp_rounding : entity is "DAT_WIDTH=32 VX_gpu_pkg_INST_FRM_RDN=2 VX_gpu_pkg_INST_FRM_RMM=4 VX_gpu_pkg_INST_FRM_RNE=0 VX_gpu_pkg_INST_FRM_RTZ=1 VX_gpu_pkg_INST_FRM_RUP=3";
end entity; 

-- Generated from Verilog module VX_fp_rounding (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6520)
--   DAT_WIDTH = 32
--   VX_gpu_pkg_INST_FRM_RDN = 2
--   VX_gpu_pkg_INST_FRM_RMM = 4
--   VX_gpu_pkg_INST_FRM_RNE = 0
--   VX_gpu_pkg_INST_FRM_RTZ = 1
--   VX_gpu_pkg_INST_FRM_RUP = 3
architecture from_verilog of VX_fp_rounding is
  impure function sv2v_cast_CEDF4 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector;
  
  signal tmp_ivl_0 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6563
  signal tmp_ivl_10 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6564
  signal tmp_ivl_12 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6564
  signal tmp_ivl_15 : logic3d_vector(29 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6564
  signal tmp_ivl_16 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6564
  signal tmp_ivl_18 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6564
  signal tmp_ivl_23 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6565
  signal tmp_ivl_24 : logic3d_vector(2 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6540
  signal tmp_ivl_26 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6565
  signal tmp_ivl_3 : logic3d_vector(30 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6563
  signal tmp_ivl_5 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6563
  signal tmp_ivl_8 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6564
  signal round_up : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6539
  
  function Boolean_To_Logic(B : Boolean) return logic3d is
  begin
    if B then
      return L3D_1;
    else
      return L3D_0;
    end if;
  end function;
  
  -- Generated from function sv2v_cast_CEDF4 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6559
  impure function sv2v_cast_CEDF4 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_CEDF4_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_CEDF4_Result := inp;
    return sv2v_cast_CEDF4_Result;
  end function;
  
  function Reduce_OR(X : logic3d_vector) return logic3d is
    variable R : logic3d := L3D_0;
  begin
    for I in X'Range loop
      R := l3d_or(X(I), R);
    end loop;
    return R;
  end function;
begin
  
  sv_and_ivl_20: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => exact_zero_o,
      a => tmp_ivl_10 & tmp_ivl_18
    );
  
  sv_and_ivl_22: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_23,
      a => exact_zero_o & effective_subtraction_i
    );
  process (all) is

  begin
    if is_one(tmp_ivl_23) then
      sign_o <= tmp_ivl_26;
    else
      sign_o <= sign_i;
    end if;
  end process;
  
  -- Generated from always process in VX_fp_rounding (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6545)
  process (rnd_mode_i, round_sticky_bits_i, abs_value_i, sign_i) is
    variable Verilog_Case_Ex : unsigned(2 downto 0);
    variable Verilog_Case_Ex_1 : unsigned(1 downto 0);
    variable v_round_up : logic3d;
  begin
    v_round_up := round_up;
    Verilog_Case_Ex := l3d_to_unsigned(rnd_mode_i);
    case Verilog_Case_Ex is
      when "000" =>
        Verilog_Case_Ex_1 := l3d_to_unsigned(round_sticky_bits_i);
        case Verilog_Case_Ex_1 is
          when "00" =>
            v_round_up := L3D_0;
          when "01" =>
            v_round_up := L3D_0;
          when "10" =>
            v_round_up := abs_value_i(0);
          when "11" =>
            v_round_up := L3D_1;
          when others =>
            null;
        end case;
      when "001" =>
        v_round_up := L3D_0;
      when "010" =>
        v_round_up := l3d_and(Reduce_OR(round_sticky_bits_i), sign_i);
      when "011" =>
        v_round_up := l3d_and(Reduce_OR(round_sticky_bits_i), l3d_not(sign_i));
      when "100" =>
        v_round_up := round_sticky_bits_i(1);
      when others =>
        v_round_up := L3D_X;
    end case;
    round_up <= v_round_up;
  end process;
  
  comb_fused_0: process (round_sticky_bits_i) is
  begin
    tmp_ivl_15 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_16 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_12 := tmp_ivl_15 & round_sticky_bits_i;
    tmp_ivl_18 := Boolean_To_Logic(tmp_ivl_12 = tmp_ivl_16);
  end process;
  
  comb_fused_1: process (rnd_mode_i) is
  begin
    tmp_ivl_24 := logic3d_vector'(L3D_0, L3D_1, L3D_0);
    tmp_ivl_26 := Boolean_To_Logic(rnd_mode_i = tmp_ivl_24);
  end process;
  
  comb_fused_2: process (abs_value_i, round_up) is
  begin
    tmp_ivl_3 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_0 := tmp_ivl_3 & round_up;
    tmp_ivl_5 := sv2v_cast_CEDF4(tmp_ivl_0);
    abs_rounded_o := abs_value_i + tmp_ivl_5;
  end process;
  
  comb_fused_3: process (abs_value_i) is
  begin
    tmp_ivl_8 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_10 := Boolean_To_Logic(abs_value_i = tmp_ivl_8);
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

-- Generated from Verilog module VX_fp_classifier (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5950)
--   EXP_BITS = 8
--   MAN_BITS = 23
entity VX_fp_classifier is
  port (
    exp_i : in logic3d_vector(7 downto 0);
    man_i : in logic3d_vector(22 downto 0);
    clss_o : out logic3d_vector(6 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_fp_classifier : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5950";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_fp_classifier : entity is "EXP_BITS=8 MAN_BITS=23";
end entity; 

-- Generated from Verilog module VX_fp_classifier (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5950)
--   EXP_BITS = 8
--   MAN_BITS = 23
architecture from_verilog of VX_fp_classifier is
  signal tmp_ivl_10 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5964
  signal tmp_ivl_23 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5969
  signal tmp_ivl_24 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5969
  signal tmp_ivl_28 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5970
  signal tmp_ivl_35 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5971
  signal tmp_ivl_39 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5972
  signal tmp_ivl_43 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5973
  signal tmp_ivl_47 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5974
  signal tmp_ivl_51 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5975
  signal tmp_ivl_55 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5976
  signal tmp_ivl_59 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5977
  signal tmp_ivl_8 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5964
  signal exp_ones : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5961
  signal exp_zero : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5960
  signal is_inf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5967
  signal is_nan : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5968
  signal is_normal : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5964
  signal is_quiet : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5970
  signal is_signaling : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5969
  signal is_subnormal : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5966
  signal is_zero : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5965
  signal man_non_zero : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5962
  signal man_zero : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5963
  
  function Reduce_OR(X : logic3d_vector) return logic3d is
    variable R : logic3d := L3D_0;
  begin
    for I in X'Range loop
      R := l3d_or(X(I), R);
    end loop;
    return R;
  end function;
  
  function Reduce_AND(X : logic3d_vector) return logic3d is
    variable R : logic3d := L3D_1;
  begin
    for I in X'Range loop
      R := l3d_and(X(I), R);
    end loop;
    return R;
  end function;
  signal LPM_d0_ivl_0 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_0_u1 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_0_u2 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_4 : logic3d_vector(22 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_4_u1 : logic3d_vector(22 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_4_u2 : logic3d_vector(22 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_60 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_60_u1 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_60_u2 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_0_u3 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_4_u3 : logic3d_vector(22 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_0_u4 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_4_u4 : logic3d_vector(22 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_60_u3 : logic3d_vector(6 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_60_u4 : logic3d_vector(6 downto 0) := (others => L3D_X);
begin
  
  sv_and_ivl_12: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_normal,
      a => tmp_ivl_8 & tmp_ivl_10
    );
  
  sv_and_ivl_14: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_zero,
      a => exp_zero & man_zero
    );
  
  sv_and_ivl_16: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_subnormal,
      a => exp_zero & man_non_zero
    );
  
  sv_and_ivl_18: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_inf,
      a => exp_ones & man_zero
    );
  
  sv_and_ivl_20: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_nan,
      a => exp_ones & man_non_zero
    );
  
  sv_and_ivl_26: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_signaling,
      a => is_nan & tmp_ivl_24
    );
  process (all) is

  begin
    tmp_ivl_28 <= l3d_not(is_signaling);
  end process;
  
  sv_and_ivl_30: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => is_quiet,
      a => is_nan & tmp_ivl_28
    );
  
  comb_fused_0: process (is_inf, is_nan, is_normal, is_quiet, is_signaling, is_subnormal, is_zero) is
  begin
    tmp_ivl_35 := is_normal;
    tmp_ivl_39 := is_zero;
    tmp_ivl_43 := is_subnormal;
    tmp_ivl_47 := is_inf;
    tmp_ivl_51 := is_nan;
    tmp_ivl_55 := is_quiet;
    tmp_ivl_59 := is_signaling;
    clss_o := tmp_ivl_35 & tmp_ivl_39 & tmp_ivl_43 & tmp_ivl_47 & tmp_ivl_51 & tmp_ivl_55 & tmp_ivl_59;
  end process;
  
  comb_fused_1: process (exp_i) is
  begin
    exp_zero := l3d_not(Reduce_OR(exp_i));
    tmp_ivl_8 := l3d_not(exp_zero);
  end process;
  
  comb_fused_2: process (exp_i) is
  begin
    exp_ones := Reduce_AND(exp_i);
    tmp_ivl_10 := l3d_not(exp_ones);
  end process;
  
  comb_fused_3: process (man_i) is
  begin
    man_non_zero := Reduce_OR(man_i);
    man_zero := l3d_not(man_non_zero);
  end process;
  
  comb_fused_4: process (man_i) is
  begin
    tmp_ivl_23 := man_i(22);
    tmp_ivl_24 := l3d_not(tmp_ivl_23);
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

-- Generated from Verilog module VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5979)
--   EXCEPT_ENABLE = 1
--   F32_BIAS = 127
--   F32_EXP = 8
--   F32_MAN = 23
--   F64_BIAS = 1023
--   F64_EXP = 11
--   F64_MAN = 52
--   FLEN = 32
--   HAS_D = 0
--   LATENCY = 5
--   LZC_RESULT_WIDTH = 5
--   OUT_REG = 1
--   STG2_CYC = 0
--   SUBNORM_ENABLE = 1
--   SUPER_EXP = 8
--   SUPER_MAN = 23
--   S_EXP_WIDTH = 12
--   S_MAN_WIDTH = 32
--   VX_gpu_pkg_INST_FRM_BITS = 3
entity VX_fcvt_unit is
  port (
    clk : in logic3d;
    reset : in logic3d;
    enable : in logic3d;
    mask : in logic3d;
    frm : in logic3d_vector(2 downto 0);
    is_itof : in logic3d;
    is_ftoi : in logic3d;
    is_f2f : in logic3d;
    is_signed : in logic3d;
    is_int64 : in logic3d;
    src_fmt : in logic3d;
    dst_fmt : in logic3d;
    dataa : in logic3d_vector(31 downto 0);
    result : out logic3d_vector(31 downto 0);
    fflags : out logic3d_vector(4 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of VX_fcvt_unit : entity is "/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5979";
  attribute nvc_verilog_params : string;
  attribute nvc_verilog_params of VX_fcvt_unit : entity is "EXCEPT_ENABLE=1 F32_BIAS=127 F32_EXP=8 F32_MAN=23 F64_BIAS=1023 F64_EXP=11 F64_MAN=52 FLEN=32 HAS_D=0 LATENCY=5 LZC_RESULT_WIDTH=5 OUT_REG=1 STG2_CYC=0 SUBNORM_ENABLE=1 SUPER_EXP=8 SUPER_MAN=23 S_EXP_WIDTH=12 S_MAN_WIDTH=32 VX_gpu_pkg_INST_FRM_BITS=3";
end entity; 

-- Generated from Verilog module VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5979)
--   EXCEPT_ENABLE = 1
--   F32_BIAS = 127
--   F32_EXP = 8
--   F32_MAN = 23
--   F64_BIAS = 1023
--   F64_EXP = 11
--   F64_MAN = 52
--   FLEN = 32
--   HAS_D = 0
--   LATENCY = 5
--   LZC_RESULT_WIDTH = 5
--   OUT_REG = 1
--   STG2_CYC = 0
--   SUBNORM_ENABLE = 1
--   SUPER_EXP = 8
--   SUPER_MAN = 23
--   S_EXP_WIDTH = 12
--   S_MAN_WIDTH = 32
--   VX_gpu_pkg_INST_FRM_BITS = 3
architecture from_verilog of VX_fcvt_unit is
  impure function sv2v_cast_FEB7F_signed (
    inp : logic3d_vector(7 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_FEB7F (
    inp : logic3d_vector(7 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_C255F (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_99F89_signed (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_99F89 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_8 (
    inp : logic3d_vector(7 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_7_signed (
    inp : logic3d_vector(6 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_7 (
    inp : logic3d_vector(6 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_6_signed (
    inp : logic3d_vector(5 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_64 (
    inp : logic3d_vector(63 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_36466_signed (
    inp : logic3d_vector(11 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_36466 (
    inp : logic3d_vector(11 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_16 (
    inp : logic3d_vector(15 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_11 (
    inp : logic3d_vector(10 downto 0)
  ) 
  return logic3d_vector;
  
  signal tmp_ivl_1 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6024
  signal tmp_ivl_133 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6174
  signal tmp_ivl_136 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6174
  signal tmp_ivl_137 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6022
  signal tmp_ivl_140 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6174
  signal tmp_ivl_141 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6019
  signal tmp_ivl_144 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6174
  signal tmp_ivl_145 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6174
  signal tmp_ivl_15 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6045
  signal tmp_ivl_152 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_154 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_156 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_159 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_161 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_162 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_164 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_167 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_168 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal tmp_ivl_173 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6197
  signal tmp_ivl_18 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6045
  signal tmp_ivl_193 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6201
  signal tmp_ivl_196 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6201
  signal tmp_ivl_199 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6023
  signal tmp_ivl_202 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6202
  signal tmp_ivl_203 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6020
  signal tmp_ivl_206 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6202
  signal tmp_ivl_211 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_213 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_216 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_217 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_219 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_22 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6046
  signal tmp_ivl_222 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_223 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_225 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_228 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_229 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal tmp_ivl_233 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6205
  signal tmp_ivl_235 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6205
  signal tmp_ivl_237 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6205
  signal tmp_ivl_24 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6046
  signal tmp_ivl_241 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6206
  signal tmp_ivl_244 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6206
  signal tmp_ivl_245 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6206
  signal tmp_ivl_249 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6207
  signal tmp_ivl_252 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6207
  signal tmp_ivl_258 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6203
  signal tmp_ivl_260 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6247
  signal tmp_ivl_283 : logic3d_vector(32 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6251
  signal tmp_ivl_285 : logic3d_vector(64 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6251
  signal tmp_ivl_296 : logic3d_vector(30 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6255
  signal tmp_ivl_299 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6022
  signal tmp_ivl_302 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6260
  signal tmp_ivl_303 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6019
  signal tmp_ivl_306 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6260
  signal tmp_ivl_309 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6269
  signal tmp_ivl_31 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6074
  signal tmp_ivl_312 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6269
  signal tmp_ivl_313 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6269
  signal tmp_ivl_316 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6269
  signal tmp_ivl_318 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6269
  signal tmp_ivl_323 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6275
  signal tmp_ivl_325 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6275
  signal tmp_ivl_328 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6275
  signal tmp_ivl_330 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6275
  signal tmp_ivl_333 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal tmp_ivl_336 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal tmp_ivl_337 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal tmp_ivl_339 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal tmp_ivl_34 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6074
  signal tmp_ivl_341 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal tmp_ivl_343 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal tmp_ivl_347 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6281
  signal tmp_ivl_350 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6281
  signal tmp_ivl_351 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6281
  signal tmp_ivl_353 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6281
  signal tmp_ivl_358 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6319
  signal tmp_ivl_37 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_383 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6335
  signal tmp_ivl_386 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6335
  signal tmp_ivl_389 : logic3d_vector(15 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6340
  signal tmp_ivl_392 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6340
  signal tmp_ivl_395 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6341
  signal tmp_ivl_397 : logic3d_vector(15 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6341
  signal tmp_ivl_40 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_401 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6342
  signal tmp_ivl_404 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6342
  signal tmp_ivl_407 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6342
  signal tmp_ivl_410 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6342
  signal tmp_ivl_42 : logic3d_vector(51 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_420 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6351
  signal tmp_ivl_421 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6351
  signal tmp_ivl_424 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6351
  signal tmp_ivl_426 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6351
  signal tmp_ivl_429 : logic3d_vector(22 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6352
  signal tmp_ivl_43 : logic3d_vector(52 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_432 : logic3d_vector(22 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6352
  signal tmp_ivl_440 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6406
  signal tmp_ivl_443 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal tmp_ivl_445 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal tmp_ivl_447 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal tmp_ivl_449 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal tmp_ivl_451 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal tmp_ivl_453 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal tmp_ivl_457 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal tmp_ivl_459 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal tmp_ivl_46 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_461 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal tmp_ivl_463 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal tmp_ivl_465 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal tmp_ivl_467 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal tmp_ivl_472 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal tmp_ivl_474 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal tmp_ivl_476 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal tmp_ivl_478 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal tmp_ivl_48 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_480 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal tmp_ivl_482 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal tmp_ivl_486 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal tmp_ivl_488 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal tmp_ivl_490 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal tmp_ivl_491 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal tmp_ivl_494 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal tmp_ivl_495 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal tmp_ivl_5 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6024
  signal tmp_ivl_50 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_500 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6411
  signal tmp_ivl_502 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6411
  signal tmp_ivl_504 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6411
  signal tmp_ivl_506 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6411
  signal tmp_ivl_508 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6411
  signal tmp_ivl_511 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6412
  signal tmp_ivl_513 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6412
  signal tmp_ivl_516 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6412
  signal tmp_ivl_52 : logic3d_vector(22 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_520 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_522 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_524 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_526 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_528 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_529 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_53 : logic3d_vector(23 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_532 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_533 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_536 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal tmp_ivl_542 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6514
  signal tmp_ivl_55 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_58 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_60 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_61 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal tmp_ivl_65 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6023
  signal tmp_ivl_68 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6084
  signal tmp_ivl_69 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6020
  signal tmp_ivl_72 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6084
  signal tmp_ivl_75 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6098
  signal tmp_ivl_77 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6098
  signal tmp_ivl_79 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6098
  signal tmp_ivl_82 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6098
  signal tmp_ivl_85 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6015
  signal tmp_ivl_88 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6015
  signal tmp_ivl_9 : logic3d := L3D_X;  -- Temporary created at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6024
  signal sig_sv2v_0 : logic3d := L3D_0;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:5996
  signal abs_xlen_64 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6342
  signal align_shamt_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6208
  signal align_shamt_s4 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6238
  signal aligned_mant_full_s4 : logic3d_vector(64 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6251
  signal aligned_mant_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6252
  signal denorm_sh_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6207
  signal dst_bias_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6202
  signal dst_d_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6127
  signal dst_d_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6158
  signal dst_d_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6185
  signal dst_d_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6232
  signal dst_d_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6304
  signal dst_exp_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6203
  signal dst_is_d : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6031
  signal dst_man_w_s4 : logic3d_vector(5 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6260
  signal f2f : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6032
  signal f2f_narrow_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6204
  signal f2f_nv_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6356
  signal f2f_nx_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6357
  signal f2f_of_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6206
  signal f2f_of_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6234
  signal f2f_of_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6306
  signal f2f_uf_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6205
  signal f2f_uf_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6233
  signal f2f_uf_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6305
  signal f2i_s32_neg_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6410
  signal f2i_s32_pos_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6409
  signal f2i_s64_neg_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6421
  signal f2i_s64_pos_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6420
  signal f2i_shamt_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6201
  signal f2i_u32_neg_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6411
  signal f2i_u32_pos_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6413
  signal f2i_u64_neg_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6422
  signal f2i_u64_pos_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6414
  signal f32_boxed : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6354
  signal f32_man_ovf : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6346
  signal fclass : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6056
  signal fclass32 : resolved_logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6047
  signal fclass_s1 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6129
  signal fclass_s2 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6160
  signal fclass_s3 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6187
  signal fclass_s4 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6236
  signal fclass_s5 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6308
  signal final_exp_16 : logic3d_vector(15 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6340
  signal final_exp_s3 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6223
  signal final_exp_s4 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6239
  signal final_exp_s5 : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6311
  signal final_fflags_s5 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6432
  signal final_result_s5 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6500
  signal fp32_exp : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6351
  signal fp32_man : logic3d_vector(22 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6352
  signal fp_32_res : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6353
  signal fp_dst_res : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6355
  signal fp_guard_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6275
  signal fp_mant_offset_s2 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6174
  signal fp_sticky_mask_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6280
  signal fp_trunc_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6270
  signal fp_trunc_sh_s4 : logic3d_vector(6 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6269
  signal fp_unpacked_mant : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6079
  signal frm_s1 : logic3d_vector(2 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6128
  signal frm_s2 : logic3d_vector(2 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6159
  signal frm_s3 : logic3d_vector(2 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6186
  signal frm_s4 : logic3d_vector(2 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6235
  signal frm_s5 : logic3d_vector(2 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6307
  signal guard_bit_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6253
  signal i_mag : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6100
  signal i_mag_raw : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6099
  signal i_sign : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6098
  signal input_fp_sgn : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6046
  signal input_sign_s0 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6103
  signal input_sign_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6125
  signal input_sign_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6155
  signal input_sign_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6182
  signal input_sign_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6229
  signal input_sign_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6301
  signal int_32_res : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6344
  signal int_64_res : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6345
  signal is_f2f_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6122
  signal is_f2f_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6152
  signal is_f2f_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6179
  signal is_f2f_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6226
  signal is_f2f_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6298
  signal is_ftoi_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6121
  signal is_ftoi_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6151
  signal is_ftoi_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6178
  signal is_ftoi_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6225
  signal is_ftoi_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6297
  signal is_int64_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6124
  signal is_int64_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6154
  signal is_int64_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6181
  signal is_int64_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6228
  signal is_int64_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6300
  signal is_itof_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6120
  signal is_itof_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6150
  signal is_itof_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6177
  signal is_itof_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6224
  signal is_itof_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6296
  signal is_signed_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6123
  signal is_signed_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6153
  signal is_signed_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6180
  signal is_signed_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6227
  signal is_signed_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6299
  signal mant_is_nonzero_s1 : resolved_logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6143
  signal mant_is_zero_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6149
  signal mant_is_zero_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6156
  signal mant_is_zero_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6183
  signal mant_is_zero_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6230
  signal mant_is_zero_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6302
  signal mask_pipe : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6033
  signal nan_inf_32 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6407
  signal nan_inf_64 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6408
  signal norm_exp_s2 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6176
  signal norm_exp_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6189
  signal norm_mant_s2 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6175
  signal norm_mant_s3 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6188
  signal norm_mant_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6237
  signal out_fflags_s5 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6506
  signal pre_round_abs_s4 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6283
  signal pre_round_abs_s5 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6310
  signal renorm_shamt_s1 : resolved_logic3d_vector(4 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6142
  signal renorm_shamt_s2 : logic3d_vector(4 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6163
  signal res_val_32 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6431
  signal res_val_64 : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6430
  signal round_bit_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6254
  signal round_carry_out_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6412
  signal round_sticky_bits_s4 : logic3d_vector(1 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6282
  signal round_sticky_bits_s5 : logic3d_vector(1 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6309
  signal rounded_abs_s5 : resolved_logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6323
  signal rounded_sign_s5 : resolved_logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6324
  signal safe_dataa : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6045
  signal safe_dst_exp : logic3d_vector(15 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6341
  signal safe_int_res : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6343
  signal safe_rounded_abs : logic3d_vector(63 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6335
  signal src_bias_s : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6084
  signal src_d_s1 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6126
  signal src_d_s2 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6157
  signal src_d_s3 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6184
  signal src_d_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6231
  signal src_d_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6303
  signal src_daz : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6074
  signal src_exp_raw : logic3d_vector(7 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6085
  signal src_is_d : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6030
  signal stg2_mask : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6040
  signal sticky_bit_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6255
  signal sticky_red_s4 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6281
  signal unpacked_exp_s0 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6102
  signal unpacked_exp_s1 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6131
  signal unpacked_exp_s2 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6162
  signal unpacked_exp_s3 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6190
  signal unpacked_exp_s4 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6240
  signal unpacked_exp_s5 : logic3d_vector(11 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6312
  signal unpacked_mant_s0 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6101
  signal unpacked_mant_s1 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6130
  signal unpacked_mant_s2 : logic3d_vector(31 downto 0) := (others => L3D_X);  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6161
  signal use_neg_sat_s5 : logic3d := L3D_X;  -- Declared at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6406
  signal LPM_d3_ivl_98 : logic3d_vector(2 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_16 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_548 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_549 : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal LO_ivl_95 : logic3d := L3D_X;
  signal LO_ivl_114 : logic3d := L3D_X;
  signal LO_ivl_174 : logic3d := L3D_X;
  signal LO_ivl_261 : logic3d := L3D_X;
  signal LO_ivl_359 : logic3d := L3D_X;
  signal LO_ivl_543 : logic3d := L3D_X;
  signal LPM_q_ivl_27 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_29 : logic3d_vector(22 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_98 : logic3d_vector(61 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_100 : logic3d_vector(61 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_117 : logic3d_vector(67 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_119 : logic3d_vector(67 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_177 : logic3d_vector(74 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_179 : logic3d_vector(74 downto 0) := (others => L3D_X);
  
  function Boolean_To_Logic(B : Boolean) return logic3d is
  begin
    if B then
      return L3D_1;
    else
      return L3D_0;
    end if;
  end function;
  signal LPM_q_ivl_264 : logic3d_vector(84 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_266 : logic3d_vector(84 downto 0) := (others => L3D_X);
  
  function Reduce_OR(X : logic3d_vector) return logic3d is
    variable R : logic3d := L3D_0;
  begin
    for I in X'Range loop
      R := l3d_or(X(I), R);
    end loop;
    return R;
  end function;
  signal LPM_q_ivl_362 : logic3d_vector(74 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_364 : logic3d_vector(74 downto 0) := (others => L3D_X);
  signal LPM_q_ivl_546 : logic3d_vector(36 downto 0) := (others => L3D_X);
  signal LPM_d0_ivl_548 : logic3d_vector(36 downto 0) := (others => L3D_X);
  signal LPM_ivl_94 : logic3d := L3D_X;
  signal LPM_d10_ivl_98 : logic3d := L3D_X;
  signal LPM_d8_ivl_98 : logic3d := L3D_X;
  signal LPM_ivl_80 : logic3d := L3D_X;
  
  component VX_fp_classifier is
    port (
      exp_i : in logic3d_vector(7 downto 0);
      man_i : in logic3d_vector(22 downto 0);
      clss_o : out logic3d_vector(6 downto 0)
    );
  end component;
  
  component VX_fp_rounding is
    port (
      abs_value_i : in logic3d_vector(31 downto 0);
      sign_i : in logic3d;
      round_sticky_bits_i : in logic3d_vector(1 downto 0);
      rnd_mode_i : in logic3d_vector(2 downto 0);
      effective_subtraction_i : in logic3d;
      abs_rounded_o : out logic3d_vector(31 downto 0);
      sign_o : out logic3d;
      exact_zero_o : buffer logic3d
    );
  end component;
  
  component VX_lzc is
    port (
      data_in : in logic3d_vector(31 downto 0);
      data_out : out logic3d_vector(4 downto 0);
      valid_out : out logic3d
    );
  end component;
  
  component VX_pipe_register4 is
    port (
      clk : in logic3d;
      reset : in logic3d;
      enable : in logic3d;
      data_in : in logic3d_vector(61 downto 0);
      data_out : out logic3d_vector(61 downto 0)
    );
  end component;
  
  component VX_pipe_register5 is
    port (
      clk : in logic3d;
      reset : in logic3d;
      enable : in logic3d;
      data_in : in logic3d_vector(67 downto 0);
      data_out : out logic3d_vector(67 downto 0)
    );
  end component;
  
  component VX_pipe_register6 is
    port (
      clk : in logic3d;
      reset : in logic3d;
      enable : in logic3d;
      data_in : in logic3d_vector(74 downto 0);
      data_out : out logic3d_vector(74 downto 0)
    );
  end component;
  
  component VX_pipe_register7 is
    port (
      clk : in logic3d;
      reset : in logic3d;
      enable : in logic3d;
      data_in : in logic3d_vector(84 downto 0);
      data_out : out logic3d_vector(84 downto 0)
    );
  end component;
  
  component VX_pipe_register8 is
    port (
      clk : in logic3d;
      reset : in logic3d;
      enable : in logic3d;
      data_in : in logic3d_vector(36 downto 0);
      data_out : out logic3d_vector(36 downto 0)
    );
  end component;
  
  -- Generated from function sv2v_cast_11 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6358
  impure function sv2v_cast_11 (
    inp : logic3d_vector(10 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_11_Result : logic3d_vector(10 downto 0);
  begin
    sv2v_cast_11_Result := inp;
    return sv2v_cast_11_Result;
  end function;
  
  -- Generated from function sv2v_cast_16 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6336
  impure function sv2v_cast_16 (
    inp : logic3d_vector(15 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_16_Result : logic3d_vector(15 downto 0);
  begin
    sv2v_cast_16_Result := inp;
    return sv2v_cast_16_Result;
  end function;
  
  -- Generated from function sv2v_cast_32 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6362
  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_32_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_32_Result := inp;
    return sv2v_cast_32_Result;
  end function;
  
  -- Generated from function sv2v_cast_36466 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6104
  impure function sv2v_cast_36466 (
    inp : logic3d_vector(11 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_36466_Result : logic3d_vector(11 downto 0);
  begin
    sv2v_cast_36466_Result := inp;
    return sv2v_cast_36466_Result;
  end function;
  
  -- Generated from function sv2v_cast_36466_signed at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6080
  impure function sv2v_cast_36466_signed (
    inp : logic3d_vector(11 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_36466_signed_Result : logic3d_vector(11 downto 0);
  begin
    sv2v_cast_36466_signed_Result := inp;
    return sv2v_cast_36466_signed_Result;
  end function;
  
  -- Generated from function sv2v_cast_64 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6041
  impure function sv2v_cast_64 (
    inp : logic3d_vector(63 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_64_Result : logic3d_vector(63 downto 0);
  begin
    sv2v_cast_64_Result := inp;
    return sv2v_cast_64_Result;
  end function;
  
  -- Generated from function sv2v_cast_6_signed at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6256
  impure function sv2v_cast_6_signed (
    inp : logic3d_vector(5 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_6_signed_Result : logic3d_vector(5 downto 0);
  begin
    sv2v_cast_6_signed_Result := inp;
    return sv2v_cast_6_signed_Result;
  end function;
  
  -- Generated from function sv2v_cast_7 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6265
  impure function sv2v_cast_7 (
    inp : logic3d_vector(6 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_7_Result : logic3d_vector(6 downto 0);
  begin
    sv2v_cast_7_Result := inp;
    return sv2v_cast_7_Result;
  end function;
  
  -- Generated from function sv2v_cast_7_signed at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6261
  impure function sv2v_cast_7_signed (
    inp : logic3d_vector(6 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_7_signed_Result : logic3d_vector(6 downto 0);
  begin
    sv2v_cast_7_signed_Result := inp;
    return sv2v_cast_7_signed_Result;
  end function;
  
  -- Generated from function sv2v_cast_8 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6347
  impure function sv2v_cast_8 (
    inp : logic3d_vector(7 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_8_Result : logic3d_vector(7 downto 0);
  begin
    sv2v_cast_8_Result := inp;
    return sv2v_cast_8_Result;
  end function;
  
  -- Generated from function sv2v_cast_99F89 at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6075
  impure function sv2v_cast_99F89 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_99F89_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_99F89_Result := inp;
    return sv2v_cast_99F89_Result;
  end function;
  
  -- Generated from function sv2v_cast_99F89_signed at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6276
  impure function sv2v_cast_99F89_signed (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_99F89_signed_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_99F89_signed_Result := inp;
    return sv2v_cast_99F89_signed_Result;
  end function;
  
  -- Generated from function sv2v_cast_C255F at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6271
  impure function sv2v_cast_C255F (
    inp : logic3d_vector(4 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_C255F_Result : logic3d_vector(4 downto 0);
  begin
    sv2v_cast_C255F_Result := inp;
    return sv2v_cast_C255F_Result;
  end function;
  
  -- Generated from function sv2v_cast_FEB7F at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6086
  impure function sv2v_cast_FEB7F (
    inp : logic3d_vector(7 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_FEB7F_Result : logic3d_vector(7 downto 0);
  begin
    sv2v_cast_FEB7F_Result := inp;
    return sv2v_cast_FEB7F_Result;
  end function;
  
  -- Generated from function sv2v_cast_FEB7F_signed at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6219
  impure function sv2v_cast_FEB7F_signed (
    inp : logic3d_vector(7 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_FEB7F_signed_Result : logic3d_vector(7 downto 0);
  begin
    sv2v_cast_FEB7F_signed_Result := inp;
    return sv2v_cast_FEB7F_signed_Result;
  end function;
  
  function Ternary_Unsigned(T : Boolean; X, Y : logic3d_vector) return logic3d_vector is
  begin
    if T then return X; else return Y; end if;
  end function;
  
  function Ternary_Logic(T : Boolean; X, Y : logic3d) return logic3d is
  begin
    if T then return X; else return Y; end if;
  end function;
begin
  
  sv_and_ivl_4: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => src_is_d,
      a => tmp_ivl_1 & src_fmt
    );
  
  sv_and_ivl_8: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => dst_is_d,
      a => tmp_ivl_5 & dst_fmt
    );
  
  sv_and_ivl_12: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2f,
      a => tmp_ivl_9 & is_f2f
    );
  process (all) is

  begin
    stg2_mask <= mask;
  end process;
  
  sv_and_ivl_36: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => src_daz,
      a => tmp_ivl_31 & tmp_ivl_34
    );
  
  sv_and_ivl_83: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => i_sign,
      a => tmp_ivl_82 & is_signed
    );
  
  sv_and_ivl_95: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => LO_ivl_95,
      a => enable & mask
    );
  
  sv_and_ivl_114: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => LO_ivl_114,
      a => enable & stg2_mask
    );
  
  sv_and_ivl_174: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => LO_ivl_174,
      a => enable & tmp_ivl_173
    );
  
  sv_and_ivl_214: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_213,
      a => is_f2f_s3 & tmp_ivl_211
    );
  
  sv_and_ivl_220: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_219,
      a => tmp_ivl_213 & tmp_ivl_217
    );
  
  sv_and_ivl_226: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_225,
      a => tmp_ivl_219 & tmp_ivl_223
    );
  
  sv_and_ivl_232: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2f_narrow_s3,
      a => tmp_ivl_225 & tmp_ivl_229
    );
  
  sv_and_ivl_240: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2f_uf_s3,
      a => f2f_narrow_s3 & tmp_ivl_237
    );
  
  sv_and_ivl_248: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2f_of_s3,
      a => f2f_narrow_s3 & tmp_ivl_245
    );
  
  sv_and_ivl_261: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => LO_ivl_261,
      a => enable & tmp_ivl_260
    );
  
  sv_or_ivl_352: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_351,
      a => tmp_ivl_350 & guard_bit_s4
    );
  
  sv_or_ivl_354: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_353,
      a => tmp_ivl_351 & round_bit_s4
    );
  
  sv_or_ivl_356: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => sticky_red_s4,
      a => tmp_ivl_353 & sticky_bit_s4
    );
  
  sv_and_ivl_359: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => LO_ivl_359,
      a => enable & tmp_ivl_358
    );
  
  sv_or_ivl_396: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_395,
      a => mant_is_zero_s5 & f2f_uf_s5
    );
  process (all) is

  begin
    int_64_res <= safe_int_res;
  end process;
  
  sv_and_ivl_441: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => use_neg_sat_s5,
      a => tmp_ivl_440 & input_sign_s5
    );
  
  sv_and_ivl_473: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_474,
      a => is_signed_s5 & tmp_ivl_472
    );
  
  sv_and_ivl_477: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_478,
      a => tmp_ivl_474 & tmp_ivl_476
    );
  
  sv_and_ivl_483: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2i_s32_pos_ovf,
      a => tmp_ivl_478 & tmp_ivl_482
    );
  
  sv_and_ivl_487: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_488,
      a => is_signed_s5 & tmp_ivl_486
    );
  
  sv_and_ivl_489: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_490,
      a => tmp_ivl_488 & input_sign_s5
    );
  
  sv_and_ivl_497: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2i_s32_neg_ovf,
      a => tmp_ivl_490 & tmp_ivl_495
    );
  
  sv_and_ivl_503: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_504,
      a => tmp_ivl_500 & tmp_ivl_502
    );
  
  sv_and_ivl_505: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_506,
      a => tmp_ivl_504 & rounded_sign_s5
    );
  
  sv_and_ivl_509: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2i_u32_neg_ovf,
      a => tmp_ivl_506 & tmp_ivl_508
    );
  
  sv_and_ivl_517: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => round_carry_out_s5,
      a => tmp_ivl_513 & tmp_ivl_516
    );
  
  sv_and_ivl_523: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_524,
      a => tmp_ivl_520 & tmp_ivl_522
    );
  
  sv_and_ivl_527: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_528,
      a => tmp_ivl_524 & tmp_ivl_526
    );
  
  sv_or_ivl_535: entity sv2vhdl.sv_or(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => tmp_ivl_536,
      a => tmp_ivl_533 & round_carry_out_s5
    );
  
  sv_and_ivl_537: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => f2i_u32_pos_ovf,
      a => tmp_ivl_528 & tmp_ivl_536
    );
  
  sv_and_ivl_543: entity sv2vhdl.sv_and(behavioral)
    generic map (
      n => 2
    )
    port map (
      y => LO_ivl_543,
      a => enable & tmp_ivl_542
    );
  process (all) is

  begin
    if is_one(src_is_d) then
      input_fp_sgn <= tmp_ivl_22;
    else
      input_fp_sgn <= tmp_ivl_24;
    end if;
  end process;
  process (all) is

  begin
    if is_one(src_is_d) then
      tmp_ivl_61 <= tmp_ivl_46;
    else
      tmp_ivl_61 <= tmp_ivl_60;
    end if;
  end process;
  process (all) is

  begin
    if is_one(src_daz) then
      fp_unpacked_mant <= tmp_ivl_37;
    else
      fp_unpacked_mant <= tmp_ivl_61;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_68 <= sv2v_cast_36466_signed(tmp_ivl_65);
  end process;
  process (all) is

  begin
    tmp_ivl_72 <= sv2v_cast_36466_signed(tmp_ivl_69);
  end process;
  process (all) is

  begin
    if is_one(src_is_d) then
      src_bias_s <= tmp_ivl_68;
    else
      src_bias_s <= tmp_ivl_72;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_int64) then
      tmp_ivl_79 <= tmp_ivl_75;
    else
      tmp_ivl_79 <= tmp_ivl_77;
    end if;
  end process;
  process (all) is

  begin
    if is_one(i_sign) then
      i_mag_raw <= tmp_ivl_88;
    else
      i_mag_raw <= dataa;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_int64) then
      i_mag <= i_mag_raw;
    else
      i_mag <= i_mag_raw;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_itof) then
      input_sign_s0 <= i_sign;
    else
      input_sign_s0 <= input_fp_sgn;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_140 <= sv2v_cast_36466_signed(tmp_ivl_137);
  end process;
  process (all) is

  begin
    tmp_ivl_144 <= sv2v_cast_36466_signed(tmp_ivl_141);
  end process;
  process (all) is

  begin
    if is_one(src_d_s2) then
      tmp_ivl_145 <= tmp_ivl_140;
    else
      tmp_ivl_145 <= tmp_ivl_144;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_167 <= sv2v_cast_36466_signed(tmp_ivl_164);
  end process;
  process (all) is

  begin
    if is_one(is_itof_s2) then
      tmp_ivl_168 <= tmp_ivl_167;
    else
      tmp_ivl_168 <= fp_mant_offset_s2;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_173 <= mask_pipe(0);
  end process;
  process (all) is

  begin
    tmp_ivl_202 <= sv2v_cast_36466_signed(tmp_ivl_199);
  end process;
  process (all) is

  begin
    tmp_ivl_206 <= sv2v_cast_36466_signed(tmp_ivl_203);
  end process;
  process (all) is

  begin
    if is_one(dst_d_s3) then
      dst_bias_s3 <= tmp_ivl_202;
    else
      dst_bias_s3 <= tmp_ivl_206;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_260 <= mask_pipe(1);
  end process;
  process (all) is

  begin
    tmp_ivl_302 <= sv2v_cast_6_signed(tmp_ivl_299);
  end process;
  process (all) is

  begin
    tmp_ivl_306 <= sv2v_cast_6_signed(tmp_ivl_303);
  end process;
  process (all) is

  begin
    if is_one(dst_d_s4) then
      dst_man_w_s4 <= tmp_ivl_302;
    else
      dst_man_w_s4 <= tmp_ivl_306;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_358 <= mask_pipe(2);
  end process;
  process (all) is

  begin
    is_itof_s5 <= LPM_d0_ivl_364(74);
  end process;
  process (all) is

  begin
    is_ftoi_s5 <= LPM_d0_ivl_364(73);
  end process;
  process (all) is

  begin
    is_f2f_s5 <= LPM_d0_ivl_364(72);
  end process;
  process (all) is

  begin
    mant_is_zero_s5 <= LPM_d0_ivl_364(68);
  end process;
  process (all) is

  begin
    src_d_s5 <= LPM_d0_ivl_364(67);
  end process;
  process (all) is

  begin
    dst_d_s5 <= LPM_d0_ivl_364(66);
  end process;
  process (all) is

  begin
    f2f_uf_s5 <= LPM_d0_ivl_364(65);
  end process;
  process (all) is

  begin
    f2f_of_s5 <= LPM_d0_ivl_364(64);
  end process;
  process (all) is

  begin
    frm_s5 <= LPM_d0_ivl_364(61 + 2 downto 61);
  end process;
  process (all) is

  begin
    round_sticky_bits_s5 <= LPM_d0_ivl_364(52 + 1 downto 52);
  end process;
  process (all) is

  begin
    if is_one(tmp_ivl_395) then
      safe_dst_exp <= tmp_ivl_397;
    else
      safe_dst_exp <= final_exp_16;
    end if;
  end process;
  process (all) is

  begin
    if is_one(rounded_sign_s5) then
      safe_int_res <= tmp_ivl_410;
    else
      safe_int_res <= abs_xlen_64;
    end if;
  end process;
  process (all) is

  begin
    int_32_res <= safe_int_res(0 + 31 downto 0);
  end process;
  process (all) is

  begin
    if is_one(f32_man_ovf) then
      fp32_man <= tmp_ivl_429;
    else
      fp32_man <= tmp_ivl_432;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_signed_s5) then
      tmp_ivl_447 <= tmp_ivl_443;
    else
      tmp_ivl_447 <= tmp_ivl_445;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_signed_s5) then
      tmp_ivl_453 <= tmp_ivl_449;
    else
      tmp_ivl_453 <= tmp_ivl_451;
    end if;
  end process;
  process (all) is

  begin
    if is_one(use_neg_sat_s5) then
      nan_inf_32 <= tmp_ivl_447;
    else
      nan_inf_32 <= tmp_ivl_453;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_signed_s5) then
      tmp_ivl_461 <= tmp_ivl_457;
    else
      tmp_ivl_461 <= tmp_ivl_459;
    end if;
  end process;
  process (all) is

  begin
    if is_one(is_signed_s5) then
      tmp_ivl_467 <= tmp_ivl_463;
    else
      tmp_ivl_467 <= tmp_ivl_465;
    end if;
  end process;
  process (all) is

  begin
    if is_one(use_neg_sat_s5) then
      nan_inf_64 <= tmp_ivl_461;
    else
      nan_inf_64 <= tmp_ivl_467;
    end if;
  end process;
  process (all) is

  begin
    tmp_ivl_508 <= Reduce_OR(rounded_abs_s5);
  end process;
  process (all) is

  begin
    tmp_ivl_542 <= mask_pipe(3);
  end process;
  process (all) is

  begin
    result <= LPM_d0_ivl_548(5 + 31 downto 5);
  end process;
  process (all) is

  begin
    fflags <= LPM_d0_ivl_548(0 + 4 downto 0);
  end process;
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6051
  fp_classifier32: entity work.VX_fp_classifier
    port map (
      clss_o => fclass32,
      exp_i => LPM_q_ivl_27,
      man_i => LPM_q_ivl_29
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6325
  fp_rounding: entity work.VX_fp_rounding
    port map (
      abs_rounded_o => rounded_abs_s5,
      abs_value_i => pre_round_abs_s5,
      effective_subtraction_i => L3D_0,
      rnd_mode_i => frm_s5,
      round_sticky_bits_i => round_sticky_bits_s5,
      sign_i => input_sign_s5,
      sign_o => rounded_sign_s5
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6144
  lzc: entity work.VX_lzc
    port map (
      data_in => unpacked_mant_s1,
      data_out => renorm_shamt_s1,
      valid_out => mant_is_nonzero_s1
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6135
  pipe_reg1: entity work.VX_pipe_register4
    port map (
      clk => clk,
      data_in => LPM_q_ivl_98,
      data_out => LPM_d0_ivl_100,
      enable => LO_ivl_95,
      reset => reset
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6167
  pipe_reg2: entity work.VX_pipe_register5
    port map (
      clk => clk,
      data_in => LPM_q_ivl_117,
      data_out => LPM_d0_ivl_119,
      enable => LO_ivl_114,
      reset => reset
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6194
  pipe_reg3: entity work.VX_pipe_register6
    port map (
      clk => clk,
      data_in => LPM_q_ivl_177,
      data_out => LPM_d0_ivl_179,
      enable => LO_ivl_174,
      reset => reset
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6244
  pipe_reg4: entity work.VX_pipe_register7
    port map (
      clk => clk,
      data_in => LPM_q_ivl_264,
      data_out => LPM_d0_ivl_266,
      enable => LO_ivl_261,
      reset => reset
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6316
  pipe_reg5: entity work.VX_pipe_register6
    port map (
      clk => clk,
      data_in => LPM_q_ivl_362,
      data_out => LPM_d0_ivl_364,
      enable => LO_ivl_359,
      reset => reset
    );
  
  -- Generated from instantiation at /tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6511
  pipe_reg_out: entity work.VX_pipe_register8
    port map (
      clk => clk,
      data_in => LPM_q_ivl_546,
      data_out => LPM_d0_ivl_548,
      enable => LO_ivl_543,
      reset => reset
    );
  process (all) is

  begin
    tmp_ivl_1 <= L3D_0;
  end process;
  process (all) is

  begin
    tmp_ivl_137 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_0, L3D_1, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_141 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_164 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_199 <= logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_203 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_299 <= logic3d_vector'(L3D_1, L3D_1, L3D_0, L3D_1, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_303 <= logic3d_vector'(L3D_0, L3D_1, L3D_0, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_31 <= L3D_0;
  end process;
  process (all) is

  begin
    tmp_ivl_37 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_397 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_429 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_443 <= logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_445 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_449 <= logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_451 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_457 <= logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_459 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
  end process;
  process (all) is

  begin
    tmp_ivl_463 <= logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_465 <= logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_5 <= L3D_0;
  end process;
  process (all) is

  begin
    tmp_ivl_65 <= logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_69 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_75 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_77 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
  end process;
  process (all) is

  begin
    tmp_ivl_9 <= L3D_0;
  end process;
  process (all) is

  begin
    f2f_nv_s5 <= L3D_0;
  end process;
  process (all) is

  begin
    f2f_nx_s5 <= L3D_0;
  end process;
  process (all) is

  begin
    f2i_s64_neg_ovf <= L3D_0;
  end process;
  process (all) is

  begin
    f2i_s64_pos_ovf <= L3D_0;
  end process;
  process (all) is

  begin
    f2i_u64_neg_ovf <= L3D_0;
  end process;
  process (all) is

  begin
    f2i_u64_pos_ovf <= L3D_0;
  end process;
  
  -- Generated from always process in VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6034)
  process is
    variable v_nba_mask_pipe : logic3d_vector(4 downto 0);
    variable nba_init_run : Boolean := True;
  begin
    v_nba_mask_pipe := mask_pipe;
    if rising_edge(clk) then
      if is_one(reset) then
        v_nba_mask_pipe := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        if is_one(enable) then
          v_nba_mask_pipe := mask_pipe(0 + 3 downto 0) & mask;
        end if;
      end if;
    end if;
    if nba_init_run then
      nba_init_run := False;
    else
      wait for 0 ns;
    end if;
    mask_pipe <= v_nba_mask_pipe;
    wait on clk;
  end process;
  
  -- Generated from always process in VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6108)
  process (sig_sv2v_0, is_itof, i_mag, fp_unpacked_mant, src_exp_raw, src_bias_s, fclass) is
    variable v_unpacked_exp_s0 : logic3d_vector(11 downto 0);
    variable v_unpacked_mant_s0 : logic3d_vector(31 downto 0);
  begin
    v_unpacked_mant_s0 := unpacked_mant_s0;
    v_unpacked_exp_s0 := unpacked_exp_s0;
    if is_one(sig_sv2v_0) then
    end if;
    if is_one(is_itof) then
      v_unpacked_mant_s0 := sv2v_cast_99F89(i_mag);
      v_unpacked_exp_s0 := sv2v_cast_36466_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1));
    else
      v_unpacked_mant_s0 := fp_unpacked_mant;
      v_unpacked_exp_s0 := (sv2v_cast_36466(resize(src_exp_raw, 12)) - src_bias_s) + sv2v_cast_36466(resize((L3D_0 & fclass(4)), 12));
    end if;
    unpacked_exp_s0 <= v_unpacked_exp_s0;
    unpacked_mant_s0 <= v_unpacked_mant_s0;
  end process;
  
  -- Generated from always process in VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6209)
  process (sig_sv2v_0, is_ftoi_s3, f2i_shamt_s3, f2f_uf_s3, denorm_sh_s3) is
    variable v_align_shamt_s3 : logic3d_vector(11 downto 0);
  begin
    v_align_shamt_s3 := align_shamt_s3;
    if is_one(sig_sv2v_0) then
    end if;
    if is_one(is_ftoi_s3) then
      if l3d_gt_s(f2i_shamt_s3, sv2v_cast_36466_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1))) then
        v_align_shamt_s3 := sv2v_cast_36466_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1));
      else
        v_align_shamt_s3 := Ternary_Unsigned(l3d_lt_s(l3d_resize_s(f2i_shamt_s3, 32), logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0)), logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0), f2i_shamt_s3);
      end if;
    else
      if is_one(f2f_uf_s3) then
        if l3d_gt_s(denorm_sh_s3, sv2v_cast_36466_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1))) then
          v_align_shamt_s3 := sv2v_cast_36466_signed(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1));
        else
          v_align_shamt_s3 := denorm_sh_s3;
        end if;
      else
        v_align_shamt_s3 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      end if;
    end if;
    align_shamt_s3 <= v_align_shamt_s3;
  end process;
  
  -- Generated from always process in VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6284)
  process (sig_sv2v_0, is_ftoi_s4, guard_bit_s4, round_bit_s4, sticky_bit_s4, aligned_mant_s4, fp_guard_s4, sticky_red_s4, fp_trunc_s4) is
    variable v_pre_round_abs_s4 : logic3d_vector(31 downto 0);
    variable v_round_sticky_bits_s4 : logic3d_vector(1 downto 0);
  begin
    v_round_sticky_bits_s4 := round_sticky_bits_s4;
    v_pre_round_abs_s4 := pre_round_abs_s4;
    if is_one(sig_sv2v_0) then
    end if;
    if is_one(is_ftoi_s4) then
      v_round_sticky_bits_s4 := guard_bit_s4 & l3d_or(round_bit_s4, sticky_bit_s4);
      v_pre_round_abs_s4 := aligned_mant_s4;
    else
      v_round_sticky_bits_s4 := fp_guard_s4 & sticky_red_s4;
      v_pre_round_abs_s4 := fp_trunc_s4;
    end if;
    pre_round_abs_s4 <= v_pre_round_abs_s4;
    round_sticky_bits_s4 <= v_round_sticky_bits_s4;
  end process;
  
  -- Generated from always process in VX_fcvt_unit (/tmp/claude-1002/-home-claude/50726f3c-29a3-493b-90a6-ca98ad342bc6/scratchpad/cmp/final/exec_tierB/exec.v:6433)
  process (sig_sv2v_0, is_ftoi_s5, fclass_s5, is_int64_s5, nan_inf_64, nan_inf_32, f2i_s32_pos_ovf, f2i_s32_neg_ovf, f2i_u32_neg_ovf, f2i_u32_pos_ovf, f2i_u64_pos_ovf, f2i_s64_pos_ovf, f2i_s64_neg_ovf, f2i_u64_neg_ovf, int_64_res, int_32_res, round_sticky_bits_s5, fp_dst_res, f2f_nv_s5, f2f_of_s5, f2f_uf_s5, is_f2f_s5, f2f_nx_s5) is
    variable v_res_val_32 : logic3d_vector(31 downto 0);
    variable v_res_val_64 : logic3d_vector(63 downto 0);
  begin
    v_res_val_64 := res_val_64;
    v_res_val_32 := res_val_32;
    if is_one(sig_sv2v_0) then
    end if;
    final_fflags_s5 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    v_res_val_64 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    v_res_val_32 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    if is_one(is_ftoi_s5) then
      if is_one(fclass_s5(2)) or is_one(fclass_s5(3)) then
        final_fflags_s5(4) <= L3D_1;
        if is_one(is_int64_s5) then
          v_res_val_64 := nan_inf_64;
        else
          v_res_val_64 := (nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31) & nan_inf_32(31)) & nan_inf_32;
        end if;
        v_res_val_32 := nan_inf_32;
      else
        if is_one(f2i_s32_pos_ovf) then
          final_fflags_s5(4) <= L3D_1;
          v_res_val_64 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
          v_res_val_32 := logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
        else
          if is_one(f2i_s32_neg_ovf) then
            final_fflags_s5(4) <= L3D_1;
            v_res_val_64 := logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
            v_res_val_32 := logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
          else
            if is_one(f2i_u32_neg_ovf) then
              final_fflags_s5(4) <= L3D_1;
              v_res_val_64 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
              v_res_val_32 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
            else
              if is_one(f2i_u32_pos_ovf) then
                final_fflags_s5(4) <= L3D_1;
                v_res_val_64 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
                v_res_val_32 := logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
              else
                if is_one(f2i_u64_pos_ovf) then
                  final_fflags_s5(4) <= L3D_1;
                  v_res_val_64 := logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
                  v_res_val_32 := logic3d_vector'(L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
                else
                  if is_one(f2i_s64_pos_ovf) then
                    final_fflags_s5(4) <= L3D_1;
                    v_res_val_64 := logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
                    v_res_val_32 := logic3d_vector'(L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
                  else
                    if is_one(f2i_s64_neg_ovf) then
                      final_fflags_s5(4) <= L3D_1;
                      v_res_val_64 := logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
                      v_res_val_32 := logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
                    else
                      if is_one(f2i_u64_neg_ovf) then
                        final_fflags_s5(4) <= L3D_1;
                        v_res_val_64 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
                        v_res_val_32 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
                      else
                        if is_one(is_int64_s5) then
                          v_res_val_64 := int_64_res;
                        else
                          v_res_val_64 := (int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31) & int_32_res(31)) & int_32_res;
                        end if;
                        v_res_val_32 := int_32_res;
                        final_fflags_s5(0) <= Reduce_OR(round_sticky_bits_s5);
                      end if;
                    end if;
                  end if;
                end if;
              end if;
            end if;
          end if;
        end if;
      end if;
    else
      v_res_val_64 := sv2v_cast_64(resize(fp_dst_res, 64));
      v_res_val_32 := fp_dst_res;
      final_fflags_s5(4) <= f2f_nv_s5;
      final_fflags_s5(2) <= f2f_of_s5;
      final_fflags_s5(1) <= l3d_and(f2f_uf_s5, Reduce_OR(round_sticky_bits_s5));
      final_fflags_s5(0) <= Ternary_Logic(is_one(is_f2f_s5), l3d_or(l3d_or(f2f_nx_s5, f2f_of_s5), l3d_and(f2f_uf_s5, Reduce_OR(round_sticky_bits_s5))), Reduce_OR(round_sticky_bits_s5));
    end if;
    res_val_32 <= v_res_val_32;
    res_val_64 <= v_res_val_64;
  end process;
  
  comb_fused_0: process (LPM_d0_ivl_100, mant_is_nonzero_s1, renorm_shamt_s1) is
  begin
    mant_is_zero_s1 := l3d_not(mant_is_nonzero_s1);
    is_itof_s1 := LPM_d0_ivl_100(61);
    is_ftoi_s1 := LPM_d0_ivl_100(60);
    is_f2f_s1 := LPM_d0_ivl_100(59);
    is_signed_s1 := LPM_d0_ivl_100(58);
    is_int64_s1 := LPM_d0_ivl_100(57);
    src_d_s1 := LPM_d0_ivl_100(56);
    dst_d_s1 := LPM_d0_ivl_100(55);
    input_sign_s1 := LPM_d0_ivl_100(54);
    frm_s1 := LPM_d0_ivl_100(51 + 2 downto 51);
    fclass_s1 := LPM_d0_ivl_100(44 + 6 downto 44);
    unpacked_mant_s1 := LPM_d0_ivl_100(12 + 31 downto 12);
    unpacked_exp_s1 := LPM_d0_ivl_100(0 + 11 downto 0);
    LPM_q_ivl_117 := is_itof_s1 & is_ftoi_s1 & is_f2f_s1 & is_signed_s1 & is_int64_s1 & input_sign_s1 & mant_is_zero_s1 & src_d_s1 & dst_d_s1 & frm_s1 & fclass_s1 & unpacked_mant_s1 & unpacked_exp_s1 & renorm_shamt_s1;
  end process;
  
  comb_fused_1: process (final_fflags_s5, res_val_32) is
  begin
    out_fflags_s5 := final_fflags_s5;
    final_result_s5 := res_val_32;
    LPM_q_ivl_546 := final_result_s5 & out_fflags_s5;
  end process;
  
  comb_fused_2: process (LPM_d0_ivl_119, tmp_ivl_168) is
  begin
    is_itof_s2 := LPM_d0_ivl_119(67);
    is_ftoi_s2 := LPM_d0_ivl_119(66);
    is_f2f_s2 := LPM_d0_ivl_119(65);
    is_signed_s2 := LPM_d0_ivl_119(64);
    is_int64_s2 := LPM_d0_ivl_119(63);
    input_sign_s2 := LPM_d0_ivl_119(62);
    mant_is_zero_s2 := LPM_d0_ivl_119(61);
    src_d_s2 := LPM_d0_ivl_119(60);
    dst_d_s2 := LPM_d0_ivl_119(59);
    frm_s2 := LPM_d0_ivl_119(56 + 2 downto 56);
    fclass_s2 := LPM_d0_ivl_119(49 + 6 downto 49);
    unpacked_mant_s2 := LPM_d0_ivl_119(17 + 31 downto 17);
    unpacked_exp_s2 := LPM_d0_ivl_119(5 + 11 downto 5);
    renorm_shamt_s2 := LPM_d0_ivl_119(0 + 4 downto 0);
    tmp_ivl_152 := L3D_0;
    tmp_ivl_159 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    norm_mant_s2 := unpacked_mant_s2 sll To_Integer(renorm_shamt_s2);
    tmp_ivl_154 := tmp_ivl_152 & renorm_shamt_s2;
    tmp_ivl_156 := tmp_ivl_159 & tmp_ivl_154;
    tmp_ivl_161 := sv2v_cast_36466(tmp_ivl_156);
    tmp_ivl_162 := unpacked_exp_s2 - tmp_ivl_161;
    norm_exp_s2 := tmp_ivl_162 + tmp_ivl_168;
    LPM_q_ivl_177 := is_itof_s2 & is_ftoi_s2 & is_f2f_s2 & is_signed_s2 & is_int64_s2 & input_sign_s2 & mant_is_zero_s2 & src_d_s2 & dst_d_s2 & frm_s2 & fclass_s2 & norm_mant_s2 & norm_exp_s2 & unpacked_exp_s2;
  end process;
  
  comb_fused_3: process (LPM_d0_ivl_179, align_shamt_s3, dst_bias_s3, f2f_of_s3, f2f_uf_s3) is
  begin
    is_itof_s3 := LPM_d0_ivl_179(74);
    is_ftoi_s3 := LPM_d0_ivl_179(73);
    is_f2f_s3 := LPM_d0_ivl_179(72);
    is_signed_s3 := LPM_d0_ivl_179(71);
    is_int64_s3 := LPM_d0_ivl_179(70);
    input_sign_s3 := LPM_d0_ivl_179(69);
    mant_is_zero_s3 := LPM_d0_ivl_179(68);
    src_d_s3 := LPM_d0_ivl_179(67);
    dst_d_s3 := LPM_d0_ivl_179(66);
    frm_s3 := LPM_d0_ivl_179(63 + 2 downto 63);
    fclass_s3 := LPM_d0_ivl_179(56 + 6 downto 56);
    norm_mant_s3 := LPM_d0_ivl_179(24 + 31 downto 24);
    norm_exp_s3 := LPM_d0_ivl_179(12 + 11 downto 12);
    unpacked_exp_s3 := LPM_d0_ivl_179(0 + 11 downto 0);
    tmp_ivl_193 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
    tmp_ivl_235 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_241 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
    tmp_ivl_249 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_211 := l3d_not(dst_d_s3);
    tmp_ivl_216 := fclass_s3(2);
    tmp_ivl_222 := fclass_s3(3);
    tmp_ivl_228 := fclass_s3(5);
    dst_exp_s3 := norm_exp_s3 + dst_bias_s3;
    tmp_ivl_196 := sv2v_cast_36466_signed(tmp_ivl_193);
    tmp_ivl_244 := sv2v_cast_36466_signed(tmp_ivl_241);
    tmp_ivl_252 := sv2v_cast_36466_signed(tmp_ivl_249);
    tmp_ivl_217 := l3d_not(tmp_ivl_216);
    tmp_ivl_223 := l3d_not(tmp_ivl_222);
    tmp_ivl_229 := l3d_not(tmp_ivl_228);
    tmp_ivl_233 := l3d_resize_s(dst_exp_s3, 32);
    tmp_ivl_258 := dst_exp_s3(0 + 7 downto 0);
    f2i_shamt_s3 := tmp_ivl_196 - unpacked_exp_s3;
    tmp_ivl_245 := Boolean_To_Logic(l3d_ge_s(dst_exp_s3, tmp_ivl_244));
    denorm_sh_s3 := tmp_ivl_252 - dst_exp_s3;
    tmp_ivl_237 := Boolean_To_Logic(l3d_ge_s(tmp_ivl_235, tmp_ivl_233));
    final_exp_s3 := sv2v_cast_FEB7F_signed(tmp_ivl_258);
    LPM_q_ivl_264 := is_itof_s3 & is_ftoi_s3 & is_f2f_s3 & is_signed_s3 & is_int64_s3 & input_sign_s3 & mant_is_zero_s3 & src_d_s3 & dst_d_s3 & f2f_uf_s3 & f2f_of_s3 & frm_s3 & fclass_s3 & norm_mant_s3 & align_shamt_s3 & final_exp_s3 & unpacked_exp_s3;
  end process;
  
  comb_fused_4: process (LPM_d0_ivl_266, pre_round_abs_s4, round_sticky_bits_s4) is
  begin
    is_itof_s4 := LPM_d0_ivl_266(84);
    is_ftoi_s4 := LPM_d0_ivl_266(83);
    is_f2f_s4 := LPM_d0_ivl_266(82);
    is_signed_s4 := LPM_d0_ivl_266(81);
    is_int64_s4 := LPM_d0_ivl_266(80);
    input_sign_s4 := LPM_d0_ivl_266(79);
    mant_is_zero_s4 := LPM_d0_ivl_266(78);
    src_d_s4 := LPM_d0_ivl_266(77);
    dst_d_s4 := LPM_d0_ivl_266(76);
    f2f_uf_s4 := LPM_d0_ivl_266(75);
    f2f_of_s4 := LPM_d0_ivl_266(74);
    frm_s4 := LPM_d0_ivl_266(71 + 2 downto 71);
    fclass_s4 := LPM_d0_ivl_266(64 + 6 downto 64);
    final_exp_s4 := LPM_d0_ivl_266(12 + 7 downto 12);
    unpacked_exp_s4 := LPM_d0_ivl_266(0 + 11 downto 0);
    LPM_q_ivl_362 := is_itof_s4 & is_ftoi_s4 & is_f2f_s4 & is_signed_s4 & is_int64_s4 & input_sign_s4 & mant_is_zero_s4 & src_d_s4 & dst_d_s4 & f2f_uf_s4 & f2f_of_s4 & frm_s4 & fclass_s4 & round_sticky_bits_s4 & pre_round_abs_s4 & final_exp_s4 & unpacked_exp_s4;
  end process;
  
  comb_fused_5: process (LPM_d0_ivl_266, dst_man_w_s4) is
  begin
    norm_mant_s4 := LPM_d0_ivl_266(32 + 31 downto 32);
    align_shamt_s4 := LPM_d0_ivl_266(20 + 11 downto 20);
    tmp_ivl_283 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_309 := logic3d_vector'(L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
    tmp_ivl_316 := L3D_0;
    tmp_ivl_323 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_333 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_337 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_343 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    tmp_ivl_285 := norm_mant_s4 & tmp_ivl_283;
    tmp_ivl_312 := sv2v_cast_7_signed(tmp_ivl_309);
    tmp_ivl_313 := tmp_ivl_316 & dst_man_w_s4;
    tmp_ivl_336 := sv2v_cast_99F89_signed(tmp_ivl_333);
    aligned_mant_full_s4 := tmp_ivl_285 srl To_Integer(align_shamt_s4);
    tmp_ivl_318 := sv2v_cast_7(tmp_ivl_313);
    aligned_mant_s4 := aligned_mant_full_s4(33 + 31 downto 33);
    guard_bit_s4 := aligned_mant_full_s4(32);
    round_bit_s4 := aligned_mant_full_s4(31);
    tmp_ivl_296 := aligned_mant_full_s4(0 + 30 downto 0);
    fp_trunc_sh_s4 := tmp_ivl_312 - tmp_ivl_318;
    sticky_bit_s4 := Reduce_OR(tmp_ivl_296);
    fp_trunc_s4 := aligned_mant_s4 srl To_Integer(fp_trunc_sh_s4);
    tmp_ivl_325 := fp_trunc_sh_s4 - tmp_ivl_323;
    tmp_ivl_339 := fp_trunc_sh_s4 - tmp_ivl_337;
    tmp_ivl_330 := tmp_ivl_325(0 + 4 downto 0);
    tmp_ivl_341 := tmp_ivl_336 sll To_Integer(tmp_ivl_339);
    tmp_ivl_328 := sv2v_cast_C255F(tmp_ivl_330);
    fp_sticky_mask_s4 := tmp_ivl_341 - tmp_ivl_343;
    fp_guard_s4 := l3d_bit_read(aligned_mant_s4, l3d_index(tmp_ivl_328, False));
    tmp_ivl_347 := l3d_and(aligned_mant_s4, fp_sticky_mask_s4);
    tmp_ivl_350 := Reduce_OR(tmp_ivl_347);
  end process;
  
  comb_fused_6: process (LPM_d0_ivl_364) is
  begin
    is_signed_s5 := LPM_d0_ivl_364(71);
    tmp_ivl_500 := l3d_not(is_signed_s5);
    tmp_ivl_520 := l3d_not(is_signed_s5);
  end process;
  
  comb_fused_7: process (LPM_d0_ivl_364) is
  begin
    is_int64_s5 := LPM_d0_ivl_364(70);
    tmp_ivl_472 := l3d_not(is_int64_s5);
    tmp_ivl_486 := l3d_not(is_int64_s5);
    tmp_ivl_502 := l3d_not(is_int64_s5);
    tmp_ivl_522 := l3d_not(is_int64_s5);
  end process;
  
  comb_fused_8: process (LPM_d0_ivl_364) is
  begin
    input_sign_s5 := LPM_d0_ivl_364(69);
    tmp_ivl_476 := l3d_not(input_sign_s5);
    tmp_ivl_526 := l3d_not(input_sign_s5);
  end process;
  
  comb_fused_9: process (LPM_d0_ivl_364) is
  begin
    fclass_s5 := LPM_d0_ivl_364(54 + 6 downto 54);
    tmp_ivl_440 := fclass_s5(3);
  end process;
  
  comb_fused_10: process (LPM_d0_ivl_364) is
  begin
    pre_round_abs_s5 := LPM_d0_ivl_364(20 + 31 downto 20);
    tmp_ivl_516 := Reduce_OR(pre_round_abs_s5);
  end process;
  
  comb_fused_11: process (LPM_d0_ivl_364) is
  begin
    final_exp_s5 := LPM_d0_ivl_364(12 + 7 downto 12);
    tmp_ivl_392 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_389 := tmp_ivl_392 & final_exp_s5;
    final_exp_16 := sv2v_cast_16(tmp_ivl_389);
  end process;
  
  comb_fused_12: process (LPM_d0_ivl_364) is
  begin
    unpacked_exp_s5 := LPM_d0_ivl_364(0 + 11 downto 0);
    tmp_ivl_529 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_532 := sv2v_cast_36466_signed(tmp_ivl_529);
    tmp_ivl_533 := Boolean_To_Logic(l3d_ge_s(unpacked_exp_s5, tmp_ivl_532));
  end process;
  
  comb_fused_13: process (fp32_man, rounded_abs_s5, rounded_sign_s5, safe_dst_exp) is
  begin
    f32_man_ovf := rounded_abs_s5(24);
    tmp_ivl_420 := safe_dst_exp(0 + 7 downto 0);
    tmp_ivl_424 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_421 := tmp_ivl_424 & f32_man_ovf;
    tmp_ivl_426 := sv2v_cast_8(tmp_ivl_421);
    fp32_exp := tmp_ivl_420 + tmp_ivl_426;
    fp_32_res := rounded_sign_s5 & fp32_exp & fp32_man;
    f32_boxed := fp_32_res;
    fp_dst_res := f32_boxed;
  end process;
  
  comb_fused_14: process (rounded_abs_s5) is
  begin
    tmp_ivl_480 := rounded_abs_s5(31);
    tmp_ivl_482 := tmp_ivl_480;
  end process;
  
  comb_fused_15: process (dataa, dst_is_d, f2f, fclass32, frm, input_sign_s0, is_ftoi, is_int64, is_itof, is_signed, src_is_d, tmp_ivl_79, unpacked_exp_s0, unpacked_mant_s0) is
  begin
    fclass := fclass32;
    tmp_ivl_18 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_58 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_34 := fclass(4);
    tmp_ivl_40 := fclass(6);
    tmp_ivl_50 := fclass(6);
    LPM_q_ivl_98 := is_itof & is_ftoi & f2f & is_signed & is_int64 & src_is_d & dst_is_d & input_sign_s0 & frm & fclass & unpacked_mant_s0 & unpacked_exp_s0;
    tmp_ivl_15 := tmp_ivl_18 & dataa;
    safe_dataa := sv2v_cast_64(tmp_ivl_15);
    src_exp_raw := safe_dataa(23 + 7 downto 23);
    tmp_ivl_22 := safe_dataa(63);
    tmp_ivl_24 := safe_dataa(31);
    LPM_q_ivl_27 := safe_dataa(23 + 7 downto 23);
    LPM_q_ivl_29 := safe_dataa(0 + 22 downto 0);
    tmp_ivl_42 := safe_dataa(0 + 51 downto 0);
    tmp_ivl_52 := safe_dataa(0 + 22 downto 0);
    tmp_ivl_82 := l3d_bit_read(safe_dataa, l3d_index(tmp_ivl_79, False));
    tmp_ivl_43 := tmp_ivl_40 & tmp_ivl_42;
    tmp_ivl_53 := tmp_ivl_50 & tmp_ivl_52;
    tmp_ivl_48 := tmp_ivl_43(0 + 31 downto 0);
    tmp_ivl_55 := tmp_ivl_58 & tmp_ivl_53;
    tmp_ivl_46 := sv2v_cast_99F89(tmp_ivl_48);
    tmp_ivl_60 := sv2v_cast_99F89(tmp_ivl_55);
  end process;
  
  comb_fused_16: process (tmp_ivl_145) is
  begin
    tmp_ivl_133 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1, L3D_1, L3D_1, L3D_1);
    tmp_ivl_136 := sv2v_cast_36466_signed(tmp_ivl_133);
    fp_mant_offset_s2 := tmp_ivl_136 - tmp_ivl_145;
  end process;
  
  comb_fused_17: process (rounded_abs_s5) is
  begin
    tmp_ivl_386 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_383 := tmp_ivl_386 & rounded_abs_s5;
    safe_rounded_abs := sv2v_cast_64(tmp_ivl_383);
    tmp_ivl_432 := safe_rounded_abs(0 + 22 downto 0);
  end process;
  
  comb_fused_18: process (rounded_abs_s5) is
  begin
    tmp_ivl_404 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_407 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_401 := tmp_ivl_404 & rounded_abs_s5;
    abs_xlen_64 := sv2v_cast_64(tmp_ivl_401);
    tmp_ivl_410 := tmp_ivl_407 - abs_xlen_64;
  end process;
  
  comb_fused_19: process (rounded_abs_s5) is
  begin
    tmp_ivl_491 := logic3d_vector'(L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_494 := sv2v_cast_99F89(tmp_ivl_491);
    tmp_ivl_495 := Boolean_To_Logic(rounded_abs_s5 > tmp_ivl_494);
  end process;
  
  comb_fused_20: process (rounded_abs_s5) is
  begin
    tmp_ivl_511 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_513 := Boolean_To_Logic(rounded_abs_s5 = tmp_ivl_511);
  end process;
  
  comb_fused_21: process (dataa) is
  begin
    tmp_ivl_85 := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    tmp_ivl_88 := tmp_ivl_85 - dataa;
  end process;
end architecture;

library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;
-- The first real Tier B walker build with all 119 modules admitted was
-- bit-exact except the float->int results (cycles 464..528: F2I/F2U, e.g.
-- 2.5 RNE -> 10 instead of 2).  This is VX_fcvt_unit and everything under
-- it, verbatim from the translated design, converting floats with
-- exponents 128..143 (integers 2..2^16 x mantissa) under every rounding
-- mode, signed and unsigned; y = result xor fflags.
entity r24_fcvt is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r24_fcvt is
  signal dataa : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal frm : logic3d_vector(2 downto 0) := (others => L3D_X);
  signal is_signed : logic3d := L3D_X;
  signal result : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal fflags : logic3d_vector(4 downto 0) := (others => L3D_X);
  signal one : logic3d := L3D_1;
  signal zero : logic3d := L3D_0;
begin
  dataa <= a(31) & L3D_1 & L3D_0 & L3D_0 & L3D_0 & op & a(22 downto 0);
  frm <= b(2 downto 0) when is_one(b(3)) else L3D_0 & b(1 downto 0);   -- 0..4 mostly
  is_signed <= b(4);
  u : entity work.VX_fcvt_unit
    port map (clk => clk, reset => reset, enable => one, mask => one, frm => frm,
              is_itof => zero, is_ftoi => one, is_f2f => zero, is_signed => is_signed,
              is_int64 => zero, src_fmt => zero, dst_fmt => zero,
              dataa => dataa, result => result, fflags => fflags);
  y <= result xor (fflags & b(31) & b(30) & b(29) & b(28) & b(27) & b(26) & b(25) & b(24) & b(23) & b(22) & b(21) & b(20) & b(19) & b(18) & b(17) & b(16) & b(15) & b(14) & b(13) & b(12) & b(11) & b(10) & b(9) & b(8) & b(7) & b(6) & b(5));
end architecture;
