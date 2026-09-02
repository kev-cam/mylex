// Non-zero-lsb prefix dims, both directions, variable prefix index (fix must
// still produce idx-lsb for descending and lsb-idx for ascending).
module nzlsb;
   logic [4:1][7:0] dn;   // descending, lsb=1  (commit 4ef20a7 shape)
   logic [1:3][7:0] up;   // ascending,  lsb=3
   typedef struct packed { logic [3:0] hi; logic [3:0] lo; } s_t;
   s_t [2:1] sdn;         // struct array, descending lsb=1
   s_t [1:2] sup;         // struct array, ascending lsb=2
   int i, fails;
   logic [3:0] r4;
   logic [7:0] r8;
   initial begin
      fails = 0;
      dn = 32'h44_33_22_11;   // dn[4]=44 dn[3]=33 dn[2]=22 dn[1]=11
      up = 24'h11_22_33;      // up[1]=11 up[2]=22 up[3]=33
      i = 1; r8 = dn[i][7:0]; if (r8 !== 8'h11) begin fails++; $display("DN1 FAIL %h", r8); end
      i = 4; r8 = dn[i][7:0]; if (r8 !== 8'h44) begin fails++; $display("DN4 FAIL %h", r8); end
      i = 3; r4 = dn[i][7:4]; if (r4 !== 4'h3)  begin fails++; $display("DN3 FAIL %h", r4); end
      i = 1; r8 = up[i][7:0]; if (r8 !== 8'h11) begin fails++; $display("UP1 FAIL %h", r8); end
      i = 3; r8 = up[i][7:0]; if (r8 !== 8'h33) begin fails++; $display("UP3 FAIL %h", r8); end
      i = 2; r4 = up[i][3:0]; if (r4 !== 4'h2)  begin fails++; $display("UP2 FAIL %h", r4); end
      // lvalue writes
      dn = '0; up = '0;
      for (i = 1; i <= 4; i++) dn[i][3:0] = i[3:0];
      if (dn !== 32'h04_03_02_01) begin fails++; $display("DNW FAIL %h", dn); end
      for (i = 1; i <= 3; i++) up[i][3:0] = i[3:0];
      if (up !== 24'h01_02_03) begin fails++; $display("UPW FAIL %h", up); end
      // struct arrays (collapse_array_exprs path)
      sdn = 16'hAB_CD;  // sdn[2]=AB sdn[1]=CD
      sup = 16'hAB_CD;  // sup[1]=AB sup[2]=CD
      i = 1; r4 = sdn[i].lo; if (r4 !== 4'hD) begin fails++; $display("SDN1 FAIL %h", r4); end
      i = 2; r4 = sdn[i].hi; if (r4 !== 4'hA) begin fails++; $display("SDN2 FAIL %h", r4); end
      i = 1; r4 = sup[i].hi; if (r4 !== 4'hA) begin fails++; $display("SUP1 FAIL %h", r4); end
      i = 2; r4 = sup[i].lo; if (r4 !== 4'hD) begin fails++; $display("SUP2 FAIL %h", r4); end
      if (fails == 0) $display("PASSED"); else $display("FAILED (%0d)", fails);
   end
endmodule
