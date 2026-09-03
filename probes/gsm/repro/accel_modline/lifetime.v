// scanner-only case: the SV lifetime qualifier must not be taken for the module name
module automatic PTop (input wire clk, output reg t);
  always @(posedge clk) t <= ~t;
endmodule
