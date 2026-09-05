-- Tier B census after the concat flattening: vx_wallace_mul
-- `concat-chain@seq-assign` -- the 700-operand partial-product row is a
-- chain of SCALAR process variables (the and-terms), whose rendered specs
-- overflow one sigspec buffer: the chunked path needs each leaf's width and
-- r2_width_or_operands has none for a scalar logic3d local.
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r19_bigcat_vars is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r19_bigcat_vars is
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);
begin
  y <= yr;
  process is
    variable pp : logic3d_vector(899 downto 0);
    variable t0 : logic3d;
    variable t1 : logic3d;
    variable t2 : logic3d;
    variable t3 : logic3d;
    variable t4 : logic3d;
    variable t5 : logic3d;
    variable t6 : logic3d;
    variable t7 : logic3d;
    variable t8 : logic3d;
    variable t9 : logic3d;
    variable t10 : logic3d;
    variable t11 : logic3d;
    variable t12 : logic3d;
    variable t13 : logic3d;
    variable t14 : logic3d;
    variable t15 : logic3d;
    variable t16 : logic3d;
    variable t17 : logic3d;
    variable t18 : logic3d;
    variable t19 : logic3d;
    variable t20 : logic3d;
    variable t21 : logic3d;
    variable t22 : logic3d;
    variable t23 : logic3d;
  begin
    if rising_edge(clk) then
      t0 := l3d_and(a(0), b(3));
      t1 := l3d_and(a(7), b(14));
      t2 := l3d_and(a(14), b(25));
      t3 := l3d_and(a(21), b(4));
      t4 := l3d_and(a(28), b(15));
      t5 := l3d_and(a(3), b(26));
      t6 := l3d_and(a(10), b(5));
      t7 := l3d_and(a(17), b(16));
      t8 := l3d_and(a(24), b(27));
      t9 := l3d_and(a(31), b(6));
      t10 := l3d_and(a(6), b(17));
      t11 := l3d_and(a(13), b(28));
      t12 := l3d_and(a(20), b(7));
      t13 := l3d_and(a(27), b(18));
      t14 := l3d_and(a(2), b(29));
      t15 := l3d_and(a(9), b(8));
      t16 := l3d_and(a(16), b(19));
      t17 := l3d_and(a(23), b(30));
      t18 := l3d_and(a(30), b(9));
      t19 := l3d_and(a(5), b(20));
      t20 := l3d_and(a(12), b(31));
      t21 := l3d_and(a(19), b(10));
      t22 := l3d_and(a(26), b(21));
      t23 := l3d_and(a(1), b(0));
      pp := t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11 & t12 & t13 & t14 & t15 & t16 & t17 & t18 & t19 & t20 & t21 & t22 & t23 & t0 & t1 & t2 & t3 & t4 & t5 & t6 & t7 & t8 & t9 & t10 & t11;
      yr <= pp(31 downto 0) xor pp(95 downto 64) xor pp(899 downto 868);
    end if;
    wait on clk;
  end process;
end architecture;
