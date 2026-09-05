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
  
