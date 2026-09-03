// A derived parameter default (RESETW = DATAW, the VX_pipe_register shape):
// the instantiation overrides DATAW and pins RESETW back to 1.
module dep #(parameter DATAW = 1, parameter RESETW = DATAW)
            (input clk, input rst, input [DATAW-1:0] d, output reg [DATAW-1:0] q);
  always @(posedge clk) begin
    if (rst) q[RESETW-1:0] <= {RESETW{1'b0}};
    else     q <= d;
  end
endmodule
