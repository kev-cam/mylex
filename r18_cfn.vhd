-- Item 11 (Tier B census: vx_csa_tree `function GET_CNT_AT_LEV k..`): a
-- design function the inliner rejects -- a WHILE loop stepping through the
-- carry-save tree levels, calling an if/else helper that uses l3d_mod_s /
-- l3d_div_s -- whose only call site takes tgt-vhdl temps driven by constant
-- continuous assigns:
--   tmp_ivl_92 <= "..0010"; tmp_ivl_94 <= "..1000";
--   tmp_ivl_97 <= get_cnt_at_lev(tmp_ivl_92, tmp_ivl_94);
-- The walker evaluates the call at build time (constant-driven signals fold
-- to their constants; the interpreter runs the body on the substitution
-- table) and connects the target to the result.
library ieee; use ieee.std_logic_1164.all;
library sv2vhdl; use sv2vhdl.logic3d_types_pkg.all;
entity r18_cfn is
  port (clk : in logic3d; reset : in logic3d;
        a : in logic3d_vector(31 downto 0); b : in logic3d_vector(31 downto 0);
        op : in logic3d_vector(3 downto 0); y : out logic3d_vector(31 downto 0));
end entity;
architecture from_verilog of r18_cfn is
  impure function next_lev (n_in : logic3d_vector(31 downto 0)) return logic3d_vector;
  impure function get_next_sz (n : logic3d_vector(31 downto 0); use_bal : logic3d_vector(31 downto 0)) return logic3d_vector;
  impure function get_cnt_at_lev (l : logic3d_vector(31 downto 0); start_n : logic3d_vector(31 downto 0)) return logic3d_vector;

  signal tmp_ivl_92 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_94 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_97 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal tmp_ivl_98 : logic3d_vector(31 downto 0) := (others => L3D_X);
  signal yr : logic3d_vector(31 downto 0) := (others => L3D_0);

  impure function next_lev (n_in : logic3d_vector(31 downto 0)) return logic3d_vector is
    variable next_lev_Result : logic3d_vector(31 downto 0);
    variable n_rem : logic3d_vector(31 downto 0);
  begin
    n_rem := l3d_mod_s(n_in, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1));
    if n_rem /= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0) then
      next_lev_Result := l3d_div_s(n_in, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1)) + l3d_div_s(n_in, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1)) + n_rem;
    else
      next_lev_Result := l3d_div_s(n_in, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1)) + l3d_div_s(n_in, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1));
    end if;
    return next_lev_Result;
  end function;

  impure function get_next_sz (n : logic3d_vector(31 downto 0); use_bal : logic3d_vector(31 downto 0)) return logic3d_vector is
    variable get_next_sz_Result : logic3d_vector(31 downto 0);
  begin
    if use_bal /= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0) then
      get_next_sz_Result := next_lev(n);
    else
      get_next_sz_Result := next_lev(n) + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    end if;
    return get_next_sz_Result;
  end function;

  impure function get_cnt_at_lev (l : logic3d_vector(31 downto 0); start_n : logic3d_vector(31 downto 0)) return logic3d_vector is
    variable get_cnt_at_lev_Result : logic3d_vector(31 downto 0);
    variable c : logic3d_vector(31 downto 0);
    variable k : logic3d_vector(31 downto 0);
  begin
    c := start_n;
    k := logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
    while l3d_lt_s(k, l) loop
      c := get_next_sz(c, logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1));
      k := k + logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1);
    end loop;
    get_cnt_at_lev_Result := c;
    return get_cnt_at_lev_Result;
  end function;
begin
  y <= yr;
  tmp_ivl_92 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0);
  tmp_ivl_94 <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_0, L3D_0, L3D_0);
  tmp_ivl_97 <= get_cnt_at_lev(tmp_ivl_92, tmp_ivl_94);
  tmp_ivl_98 <= get_cnt_at_lev(logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_1, L3D_1), tmp_ivl_94);
  process is
  begin
    if rising_edge(clk) then
      if is_one(reset) then
        yr <= logic3d_vector'(L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0, L3D_0);
      else
        yr <= (a + tmp_ivl_97) xor (b and tmp_ivl_98) xor (tmp_ivl_97(15 downto 0) & tmp_ivl_98(15 downto 0));
      end if;
    end if;
    wait on clk;
  end process;
end architecture;
