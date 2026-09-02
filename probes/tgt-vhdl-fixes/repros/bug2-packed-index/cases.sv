// BUG 2 case matrix: chained packed select with a VARIABLE prefix index.
// The wrong term is -(stride-1) injected by make_prefix_var_offset() when the
// prefix dimension has msb == lsb (a [0:0] dim, e.g. DEPTH=1).
module cases;
   logic [0:0][1:0]      a;   // A: outer [0:0], stride 2  -> BUG (expects -1)
   logic [1:0][1:0]      b;   // B: outer [1:0]            -> control (msb > lsb)
   logic [0:1][1:0]      c;   // C: ascending outer [0:1]  -> control
   logic [0:0][0:0]      d;   // D: outer [0:0], stride 1  -> masked (wid-1 == 0)
   logic [1:0][0:0][3:0] e;   // E: 3-D, MIDDLE dim [0:0], stride 4 -> BUG (expects -3)
   logic [0:0][1:0]      f;   // F: outer [0:0], variable FINAL bit index
   logic [0:0][7:0]      g;   // G: outer [0:0], stride 8, read side
   int i, j, k;
   logic [1:0] rd2;
   logic       rd1;
   int fails;

   initial begin
      fails = 0;
      a = '0; b = '0; c = '0; d = '0; e = '0; f = '0;

      for (i = 0; i < 1; i++) a[i][1:1] = 1'b1;
      if (a !== 2'b10) begin fails++; $display("A FAIL a=%b (want 10)", a); end

      for (i = 0; i < 2; i++) b[i][1:1] = 1'b1;
      if (b !== 4'b1010) begin fails++; $display("B FAIL b=%b (want 1010)", b); end

      for (i = 0; i < 2; i++) c[i][1:1] = 1'b1;
      if (c !== 4'b1010) begin fails++; $display("C FAIL c=%b (want 1010)", c); end

      for (i = 0; i < 1; i++) d[i][0:0] = 1'b1;
      if (d !== 1'b1) begin fails++; $display("D FAIL d=%b (want 1)", d); end

      for (i = 0; i < 2; i++)
         for (j = 0; j < 1; j++) e[i][j][3:2] = 2'b11;
      if (e !== 8'b1100_1100) begin fails++; $display("E FAIL e=%b (want 11001100)", e); end

      k = 1;
      for (i = 0; i < 1; i++) f[i][k] = 1'b1;
      if (f !== 2'b10) begin fails++; $display("F FAIL f=%b (want 10)", f); end

      // read side
      g = 8'hA5;
      rd2 = 2'b00;
      for (i = 0; i < 1; i++) rd2 = g[i][7:6];
      if (rd2 !== 2'b10) begin fails++; $display("G FAIL rd2=%b (want 10)", rd2); end
      rd1 = 1'b0;
      for (i = 0; i < 1; i++) rd1 = g[i][k];    // g[0][1] = 0
      if (rd1 !== 1'b0) begin fails++; $display("G2 FAIL rd1=%b (want 0)", rd1); end
      k = 2;
      for (i = 0; i < 1; i++) rd1 = g[i][k];    // g[0][2] = 1
      if (rd1 !== 1'b1) begin fails++; $display("G3 FAIL rd1=%b (want 1)", rd1); end

      if (fails == 0) $display("PASSED");
      else            $display("FAILED (%0d)", fails);
   end
endmodule
