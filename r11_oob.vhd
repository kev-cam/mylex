-- Item 7 (catalogue): the OOB_WriteV guarded dynamic part-select write
-- `target[idx*W +: W] = val` as tgt-vhdl renders it (Tmp := val; Idx :=
-- l3d_index(e); range guard; W-iteration loop of guarded single-bit copies).
-- (a) VX_lane_gather (exec.vhd:12392-12435): a 1-iteration while loop writes
-- 'x over the whole vector at a CONSTANT index, then the lane at isw*DATAW;
-- (b) a 4-lane packing (W=8 into 32 bits, idx = sel*8).  Once unrolled the
-- per-bit copies are dynamic single-bit writes to one target: `dyn-multi`.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r11_oob is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
  attribute nvc_verilog_src : string;
  attribute nvc_verilog_src of r11_oob : entity is "r11_oob.v:1";
end entity;

architecture from_verilog of r11_oob is
  signal result_out_data : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal packed : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  -- Generated from always process in lane_gather
  process (a, op) is
    variable i : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Tmp_9 : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Idx_9 : Integer;
    variable OOB_WriteV_Tmp_11 : logic3d_vector(31 downto 0);
    variable OOB_WriteV_Idx_11 : Integer;
  begin
    i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    while l3d_lt_s(i, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) loop
      OOB_WriteV_Tmp_9 := logic3d_vector'(L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X, L3D_X);
      OOB_WriteV_Idx_9 := l3d_index(i * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0), True);
      if (OOB_WriteV_Idx_9 >= -31) and (OOB_WriteV_Idx_9 <= 31) then
        for OOB_P in 0 to 31 loop
          if ((OOB_WriteV_Idx_9 + OOB_P) >= 0) and ((OOB_WriteV_Idx_9 + OOB_P) <= 31) then
            result_out_data(OOB_WriteV_Idx_9 + OOB_P) <= OOB_WriteV_Tmp_9(OOB_P);
          end if;
        end loop;
      end if;
      i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    end loop;
    i := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    while l3d_lt_s(i, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1)) loop
      OOB_WriteV_Tmp_11 := l3d_part_read(a, l3d_index(i * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0), True), 32);
      OOB_WriteV_Idx_11 := l3d_index(unsigned_to_l3d(Resize(l3d_to_unsigned(op(0 downto 0)), 32)) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0), False);
      if (OOB_WriteV_Idx_11 >= -31) and (OOB_WriteV_Idx_11 <= 31) then
        for OOB_P in 0 to 31 loop
          if ((OOB_WriteV_Idx_11 + OOB_P) >= 0) and ((OOB_WriteV_Idx_11 + OOB_P) <= 31) then
            result_out_data(OOB_WriteV_Idx_11 + OOB_P) <= OOB_WriteV_Tmp_11(OOB_P);
          end if;
        end loop;
      end if;
      i := i + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    end loop;
  end process;

  -- 4-lane packing: packed[sel*8 +: 8] = b[7:0]
  process (b, op) is
    variable OOB_WriteV_Tmp_12 : logic3d_vector(7 downto 0);
    variable OOB_WriteV_Idx_12 : Integer;
  begin
    packed <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    OOB_WriteV_Tmp_12 := b(7 downto 0);
    OOB_WriteV_Idx_12 := l3d_index(unsigned_to_l3d(Resize(l3d_to_unsigned(op(2 downto 1)), 32)) * logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0), False);
    if (OOB_WriteV_Idx_12 >= -7) and (OOB_WriteV_Idx_12 <= 31) then
      for OOB_P in 0 to 7 loop
        if ((OOB_WriteV_Idx_12 + OOB_P) >= 0) and ((OOB_WriteV_Idx_12 + OOB_P) <= 31) then
          packed(OOB_WriteV_Idx_12 + OOB_P) <= OOB_WriteV_Tmp_12(OOB_P);
        end if;
      end loop;
    end if;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= l3d_xor(result_out_data, packed);
      end if;
    end if;
  end process;
end architecture;
