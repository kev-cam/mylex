// BUG-2 shapes: variable prefix index into packed arrays whose outer (or
// middle) dimension has msb == lsb, non-zero lsb, ascending inner dimension,
// and 3-D. Writes go through the variable index and are checked against
// constant-index reads (and vice versa).
module t5_index;
  reg [0:0][7:0] x0;      // outer [0:0], inner descending
  reg [1:1][7:0] x1;      // outer [1:1] (lsb = 1)
  reg [0:0][0:7] xa;      // outer [0:0], inner ASCENDING
  reg [2:0][0:0][3:0] x3; // middle dim [0:0]
  reg [3:1][0:0][3:0] x4; // outer lsb 1, middle [0:0]
  integer i, k, b;
  reg [1:0] r;
  integer fails;

  initial begin
    fails = 0;
    // ---- write via variable prefix, check whole value ----
    x0 = 8'h00; i = 0; x0[i][3:2] = 2'b11;
    if (x0 !== 8'b0000_1100) begin fails++; $display("F x0 var-write [3:2]: %b", x0); end
    b = 4; x0[i][b +: 2] = 2'b11;
    if (x0 !== 8'b0011_1100) begin fails++; $display("F x0 var-write [b+:2]: %b", x0); end
    b = 7; x0[i][b -: 2] = 2'b11;
    if (x0 !== 8'b1111_1100) begin fails++; $display("F x0 var-write [b-:2]: %b", x0); end
    x0[i][1] = 1'b1;
    if (x0 !== 8'b1111_1110) begin fails++; $display("F x0 var-write [1]: %b", x0); end
    // ---- read via variable prefix, constant inner ----
    x0 = 8'b1010_0110; i = 0;
    r = x0[i][3:2];
    if (r !== 2'b01) begin fails++; $display("F x0 var-read [3:2]: %b", r); end
    r = x0[i][7:6];
    if (r !== 2'b10) begin fails++; $display("F x0 var-read [7:6]: %b", r); end
    b = 1; r = x0[i][b +: 2];
    if (r !== 2'b11) begin fails++; $display("F x0 var-read [b+:2]: %b", r); end
    // ---- outer lsb = 1 ----
    x1 = 8'h00; i = 1; x1[i][3:2] = 2'b11;
    if (x1 !== 8'h0C) begin fails++; $display("F x1 var-write: %h", x1); end
    if (x1[1][3:2] !== 2'b11) begin fails++; $display("F x1 const-read: %b", x1[1][3:2]); end
    x1 = 8'b0110_0000; r = x1[i][6:5];
    if (r !== 2'b11) begin fails++; $display("F x1 var-read: %b", r); end
    // ---- ascending inner: xa[0][0:1] are the two MSBs (canonical 7,6) ----
    xa = 8'h00; i = 0; xa[i][0:1] = 2'b11;
    if (xa !== 8'hC0) begin fails++; $display("F xa var-write: %h", xa); end
    xa = 8'h03; r = xa[i][6:7];
    if (r !== 2'b11) begin fails++; $display("F xa var-read: %b", r); end
    // ---- 3-D with middle [0:0] ----
    x3 = 12'h000; k = 1; i = 0; x3[k][i][1:0] = 2'b11;
    if (x3 !== 12'h030) begin fails++; $display("F x3 var-write k=1: %h", x3); end
    k = 2; x3[k][i][3:2] = 2'b11;
    if (x3 !== 12'hC30) begin fails++; $display("F x3 var-write k=2: %h", x3); end
    x3 = 12'h5A0; k = 1; r = x3[k][i][3:2];
    if (r !== 2'b10) begin fails++; $display("F x3 var-read: %b", r); end
    // constant outer, variable middle
    x3 = 12'h000; i = 0; x3[2][i][1:0] = 2'b11;
    if (x3 !== 12'h300) begin fails++; $display("F x3 const-outer var-middle: %h", x3); end
    // ---- outer lsb 1 with middle [0:0] ----
    x4 = 12'h000; k = 3; i = 0; x4[k][i][1:0] = 2'b11;
    if (x4 !== 12'h300) begin fails++; $display("F x4 var-write k=3: %h", x4); end
    k = 1; x4[k][i][3:0] = 4'hF;
    if (x4 !== 12'h30F) begin fails++; $display("F x4 var-write k=1: %h", x4); end
    if (fails == 0) $display("T5 PASS");
    else $display("T5 FAIL %0d", fails);
    $finish;
  end
endmodule
