// trivially-correct behavioral reference for the formal check
module pc4_gold(input [7:0] x, output [7:0] out);
  assign out = x[0] + x[1] + x[2] + x[3];
endmodule
