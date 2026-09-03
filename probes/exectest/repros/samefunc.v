// Repro: two modules each declare a function with the same name (sv2v emits
// one sv2v_cast_<hash> per module). The default-scope-instance filter keys
// function scopes by name only, so the second module's function body is
// never drawn -> "no visible declaration for CAST".
module m1(input clk, input [1:0] a, output reg [1:0] y);
  function automatic [1:0] cast; input [1:0] i; cast = i; endfunction
  if (1) begin : g
    always @(posedge clk) y <= cast(a);
  end
endmodule
module m2(input clk, input [1:0] a, output reg [1:0] y);
  function automatic [1:0] cast; input [1:0] i; cast = ~i; endfunction
  if (1) begin : g
    always @(posedge clk) y <= cast(a);
  end
endmodule
module top(input clk, input [1:0] a, output [1:0] y1, output [1:0] y2);
  m1 i1(.clk(clk), .a(a), .y(y1));
  m2 i2(.clk(clk), .a(a), .y(y2));
endmodule
