// Repro: a function declared inside a generate loop, with a formal width
// that depends on the iteration (VX_csa_tree: `function [WI-1:0]
// sv2v_cast_<hash>` with WI = W + level). Generate blocks are flattened
// into one architecture and functions were de-duplicated by bare name, so
// every level's calls bound to level 0's declaration -> "actual length 58
// does not match formal length 56". Self-check: tb_genfunc.vhd.
module top(input [7:0] a, output [3:0] y0, output [5:0] y1, output [7:0] z0, output [7:0] z1);
  genvar i;
  for (i = 0; i < 2; i = i + 1) begin : g_lvl
    localparam W = 4 + 2*i;
    function automatic [W-1:0] trunc; input [W-1:0] inp; trunc = inp; endfunction
    wire [W-1:0] t = trunc(a);         // continuous call: a is wider than W
    reg [7:0] r;
    always @(*) r = {{(8-W){1'b0}}, trunc(a)};   // procedural call
    if (i == 0) begin : g0
      assign y0 = t; assign z0 = r;
    end else begin : g1
      assign y1 = t; assign z1 = r;
    end
  end
endmodule
