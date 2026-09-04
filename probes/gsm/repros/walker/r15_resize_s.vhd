-- New (first REAL Tier A build via the RTLIL builder, invisible to the census
-- and caught by NVC_ACCEL_VERIFY=1: COMMIT_IF_1_DATA / COMMIT_IF_0_DATA
-- diverge): `l3d_resize_s(a, N)` is a SIGNED resize on the value plane --
-- the LSU's LB/LH response `sv2v_cast_32_signed(l3d_resize_s(rsp_data8, 32))`
-- (exec.vhd:12566-12592) and the multiplier's operands `l3d_resize_s(dataa,
-- 66)` (exec.vhd:6220).  The walker passed the operand through as an
-- identity and the builder zero-extended the assignment (a `rhs fitted`
-- line in the accel log: 32 bits <- 8 bits).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library sv2vhdl;
use sv2vhdl.sv_display_pkg.all;
use sv2vhdl.logic3d_types_pkg.all;
use sv2vhdl.sv_analog_pkg.all;
use sv2vhdl.sv_math_pkg.all;

entity r15_resize_s is
  port (
    clk : in logic3d;
    reset : in logic3d;
    a : in logic3d_vector(31 downto 0);
    b : in logic3d_vector(31 downto 0);
    op : in logic3d_vector(3 downto 0);
    y : out logic3d_vector(31 downto 0)
  );
end entity;

architecture from_verilog of r15_resize_s is
  impure function sv2v_cast_32_signed (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector;
  
  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector;
  
  signal rsp_data8 : logic3d_vector(7 downto 0) := (others => L3D_X);
  signal rsp_data16 : logic3d_vector(15 downto 0) := (others => L3D_X);
  signal rsp_data : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal prod_a : logic3d_vector(65 downto 0) := (others => L3D_X);
  signal prod_b : logic3d_vector(65 downto 0) := (others => L3D_X);
  signal prod : logic3d_vector(65 downto 0) := (others => L3D_X);
  signal y_r : logic3d_vector(31 downto 0) := (others => L3D_0);
  
  impure function sv2v_cast_32_signed (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_32_signed_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_32_signed_Result := inp;
    return sv2v_cast_32_signed_Result;
  end function;
  
  impure function sv2v_cast_32 (
    inp : logic3d_vector(31 downto 0)
  ) 
  return logic3d_vector is
    variable sv2v_cast_32_Result : logic3d_vector(31 downto 0);
  begin
    sv2v_cast_32_Result := inp;
    return sv2v_cast_32_Result;
  end function;
begin
  process (all) is

  begin
    y <= y_r;
  end process;

  process (all) is

  begin
    rsp_data8 <= a(7 downto 0);
    rsp_data16 <= a(15 downto 0);
  end process;

  -- LSU response sign/zero extension (VX_lsu_slice g_rsp_data)
  process (op, rsp_data8, rsp_data16, a) is
    variable Verilog_Case_Ex : unsigned(1 downto 0);
    variable v_rsp_data : logic3d_vector(31 downto 0);
  begin
    v_rsp_data := rsp_data;
    Verilog_Case_Ex := l3d_to_unsigned(op(1 downto 0));
    case Verilog_Case_Ex is
      when "00" =>
        v_rsp_data(0 + 31 downto 0) := sv2v_cast_32_signed(l3d_resize_s(rsp_data8, 32));
      when "01" =>
        v_rsp_data(0 + 31 downto 0) := sv2v_cast_32_signed(l3d_resize_s(rsp_data16, 32));
      when "10" =>
        v_rsp_data(0 + 31 downto 0) := sv2v_cast_32(resize(rsp_data8, 32));
      when others =>
        v_rsp_data(0 + 31 downto 0) := sv2v_cast_32(resize(rsp_data16, 32));
    end case;
    rsp_data <= v_rsp_data;
  end process;

  -- multiplier operands (VX_alu_muldiv g_prod_s): 33 -> 66 bit signed operands
  process (all) is

  begin
    prod_a <= l3d_resize_s(a(31) & a, 66);
    prod_b <= l3d_resize_s(b(31) & b, 66);
    prod <= prod_a * prod_b;
  end process;

  process (clk) is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        y_r <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        y_r <= l3d_xor(rsp_data, l3d_xor(prod(63 downto 32), prod(31 downto 0)));
      end if;
    end if;
  end process;
end architecture;
