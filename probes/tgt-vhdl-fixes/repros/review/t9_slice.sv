// Whole-slice selects with a variable index on msb==lsb dims, and +:/-:
// on a [0:0]-shaped FINAL dim, plus the struct-member path
// (collapse_array_exprs via check_for_struct_members).
module t9_slice;
  reg [0:0][7:0] x0;
  reg [1:1][7:0] x1;
  reg [2:0][0:0][3:0] x3;
  reg [0:0] s1;
  reg [3:0][0:0] w;
  typedef struct packed { logic [3:0] hi; logic [3:0] lo; } s_t;
  s_t [0:0] arr;
  s_t [1:1] arr1;
  integer i, k, b;
  reg [7:0] r8;
  reg [3:0] r4;
  reg r1;
  integer fails;
  initial begin
    fails = 0;
    i = 0; x0 = 8'h00; x0[i] = 8'hAB;
    if (x0 !== 8'hAB) begin fails++; $display("F x0[i] write: %h", x0); end
    x0 = 8'h5C; r8 = x0[i];
    if (r8 !== 8'h5C) begin fails++; $display("F x0[i] read: %h", r8); end
    i = 1; x1 = 8'h00; x1[i] = 8'h3D;
    if (x1 !== 8'h3D) begin fails++; $display("F x1[i] write: %h", x1); end
    r8 = x1[i];
    if (r8 !== 8'h3D) begin fails++; $display("F x1[i] read: %h", r8); end
    k = 2; i = 0; x3 = 12'h000; x3[k][i] = 4'hE;
    if (x3 !== 12'hE00) begin fails++; $display("F x3[k][i] write: %h", x3); end
    x3 = 12'h7A5; k = 1; r4 = x3[k][i];
    if (r4 !== 4'hA) begin fails++; $display("F x3[k][i] read: %h", r4); end
    k = 0; r4 = x3[k];
    if (r4 !== 4'h5) begin fails++; $display("F x3[k] read: %h", r4); end
    // [0:0] final dim, variable base +: / -:
    s1 = 1'b0; b = 0; s1[b +: 1] = 1'b1;
    if (s1 !== 1'b1) begin fails++; $display("F s1[b+:1] write: %b", s1); end
    s1 = 1'b1; r1 = s1[b -: 1];
    if (r1 !== 1'b1) begin fails++; $display("F s1[b-:1] read: %b", r1); end
    w = 4'b0000; k = 2; b = 0; w[k][b +: 1] = 1'b1;
    if (w !== 4'b0100) begin fails++; $display("F w[k][b+:1] write: %b", w); end
    w = 4'b1010; k = 3; r1 = w[k][b -: 1];
    if (r1 !== 1'b1) begin fails++; $display("F w[k][b-:1] read: %b", r1); end
    // struct member through a [0:0] / [1:1] array with a variable index
    i = 0; arr = 8'h09;
    if (arr !== 8'h09) begin fails++; $display("F arr[i].lo write: %h", arr); end
    arr = 8'h6F; r4 = arr[i].hi;
    if (r4 !== 4'h6) begin fails++; $display("F arr[i].hi read: %h", r4); end
    i = 1; arr1 = 8'hC0;
    if (arr1 !== 8'hC0) begin fails++; $display("F arr1[i].hi write: %h", arr1); end
    arr1 = 8'h3E; r4 = arr1[i].lo;
    if (r4 !== 4'hE) begin fails++; $display("F arr1[i].lo read: %h", r4); end
    if (fails == 0) $display("T9 PASS"); else $display("T9 FAIL %0d", fails);
    $finish;
  end
endmodule
