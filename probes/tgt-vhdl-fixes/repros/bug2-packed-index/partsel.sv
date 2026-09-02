// BUG 2 non-regression check: constant-index part-selects and plain 1-D
// vector part-selects (constant, +: and -:) must still lower correctly after
// the make_prefix_var_offset / collapse_array_exprs change in netmisc.cc.
// These paths call normalize_variable_base with a REAL part-select width and
// direction, which the fix deliberately leaves untouched.
module partsel;
   // 2-D packed, constant outer index (both dims), lval and rval
   logic [1:0][3:0]  p2;
   logic [0:0][3:0]  p1;   // msb == lsb outer dim, constant index
   // 1-D vectors: descending, ascending, non-zero lsb both directions
   logic [7:0]       vd;
   logic [0:7]       va;
   logic [11:4]      vnd;
   logic [4:11]      vna;
   int i;
   logic [1:0] r2;
   logic [3:0] r4;
   int fails;

   initial begin
      fails = 0;

      // ---- constant-index part-select on 2-D packed ----
      p2 = '0;
      p2[1][3:2] = 2'b11;             // bits 7:6
      p2[0][1:0] = 2'b01;             // bits 1:0
      if (p2 !== 8'b1100_0001) begin fails++; $display("P2W FAIL p2=%b (want 11000001)", p2); end
      r2 = p2[1][3:2];
      if (r2 !== 2'b11) begin fails++; $display("P2R FAIL r2=%b (want 11)", r2); end
      r2 = p2[0][1:0];
      if (r2 !== 2'b01) begin fails++; $display("P2R2 FAIL r2=%b (want 01)", r2); end

      p1 = '0;
      p1[0][3:3] = 1'b1;              // bit 3 (DEPTH=1 idiom with a constant index)
      p1[0][1:0] = 2'b10;
      if (p1 !== 4'b1010) begin fails++; $display("P1W FAIL p1=%b (want 1010)", p1); end
      r4 = p1[0][3:0];
      if (r4 !== 4'b1010) begin fails++; $display("P1R FAIL r4=%b (want 1010)", r4); end

      // ---- 1-D descending [7:0] ----
      vd = 8'h00;
      vd[5:2] = 4'b1001;              // constant part select
      if (vd !== 8'b0010_0100) begin fails++; $display("VD1 FAIL vd=%b (want 00100100)", vd); end
      i = 6; vd[i +: 2] = 2'b11;      // bits 7:6
      if (vd !== 8'b1110_0100) begin fails++; $display("VD2 FAIL vd=%b (want 11100100)", vd); end
      i = 1; vd[i -: 2] = 2'b11;      // bits 1:0
      if (vd !== 8'b1110_0111) begin fails++; $display("VD3 FAIL vd=%b (want 11100111)", vd); end
      r4 = vd[5:2];
      if (r4 !== 4'b1001) begin fails++; $display("VD4 FAIL r4=%b (want 1001)", r4); end
      i = 2; r2 = vd[i +: 2];         // bits 3:2 = 01
      if (r2 !== 2'b01) begin fails++; $display("VD5 FAIL r2=%b (want 01)", r2); end
      i = 5; r2 = vd[i -: 2];         // bits 5:4 = 10
      if (r2 !== 2'b10) begin fails++; $display("VD6 FAIL r2=%b (want 10)", r2); end

      // ---- 1-D ascending [0:7] ----
      va = 8'h00;
      va[2:5] = 4'b1001;              // va[2]=1 va[3]=0 va[4]=0 va[5]=1
      if (va !== 8'b0010_0100) begin fails++; $display("VA1 FAIL va=%b (want 00100100)", va); end
      i = 0; va[i +: 2] = 2'b11;      // va[0], va[1]
      if (va !== 8'b1110_0100) begin fails++; $display("VA2 FAIL va=%b (want 11100100)", va); end
      i = 7; va[i -: 2] = 2'b11;      // va[6], va[7]
      if (va !== 8'b1110_0111) begin fails++; $display("VA3 FAIL va=%b (want 11100111)", va); end
      r4 = va[2:5];
      if (r4 !== 4'b1001) begin fails++; $display("VA4 FAIL r4=%b (want 1001)", r4); end
      i = 2; r2 = va[i +: 2];         // va[2],va[3] = 10
      if (r2 !== 2'b10) begin fails++; $display("VA5 FAIL r2=%b (want 10)", r2); end
      i = 5; r2 = va[i -: 2];         // va[4],va[5] = 01
      if (r2 !== 2'b01) begin fails++; $display("VA6 FAIL r2=%b (want 01)", r2); end

      // ---- 1-D descending, non-zero lsb [11:4] ----
      vnd = 8'h00;
      vnd[9:6] = 4'b1001;
      if (vnd !== 8'b0010_0100) begin fails++; $display("VND1 FAIL vnd=%b (want 00100100)", vnd); end
      i = 10; vnd[i +: 2] = 2'b11;    // bits 11:10
      if (vnd !== 8'b1110_0100) begin fails++; $display("VND2 FAIL vnd=%b (want 11100100)", vnd); end
      i = 5; vnd[i -: 2] = 2'b11;     // bits 5:4
      if (vnd !== 8'b1110_0111) begin fails++; $display("VND3 FAIL vnd=%b (want 11100111)", vnd); end
      i = 6; r2 = vnd[i +: 2];        // bits 7:6 = 01
      if (r2 !== 2'b01) begin fails++; $display("VND4 FAIL r2=%b (want 01)", r2); end
      i = 9; r2 = vnd[i -: 2];        // bits 9:8 = 10
      if (r2 !== 2'b10) begin fails++; $display("VND5 FAIL r2=%b (want 10)", r2); end

      // ---- 1-D ascending, non-zero lsb [4:11] ----
      vna = 8'h00;
      vna[6:9] = 4'b1001;
      if (vna !== 8'b0010_0100) begin fails++; $display("VNA1 FAIL vna=%b (want 00100100)", vna); end
      i = 4; vna[i +: 2] = 2'b11;     // vna[4], vna[5]
      if (vna !== 8'b1110_0100) begin fails++; $display("VNA2 FAIL vna=%b (want 11100100)", vna); end
      i = 11; vna[i -: 2] = 2'b11;    // vna[10], vna[11]
      if (vna !== 8'b1110_0111) begin fails++; $display("VNA3 FAIL vna=%b (want 11100111)", vna); end
      i = 6; r2 = vna[i +: 2];        // vna[6],vna[7] = 10
      if (r2 !== 2'b10) begin fails++; $display("VNA4 FAIL r2=%b (want 10)", r2); end
      i = 9; r2 = vna[i -: 2];        // vna[8],vna[9] = 01
      if (r2 !== 2'b01) begin fails++; $display("VNA5 FAIL r2=%b (want 01)", r2); end

      if (fails == 0) $display("PASSED");
      else            $display("FAILED (%0d)", fails);
   end
endmodule
