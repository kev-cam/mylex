module r12_casez (
  input clk,
  input reset,
  input [31:0] a,
  input [31:0] b,
  input [3:0] op,
  output [31:0] y
);
  // Verilog twin of r12_casez.vhd for the accel's TEXT path (the tgt-vhdl
  // flow always carries the original Verilog behind nvc_verilog_src;
  // vhdl2vlog declines the expanded casez's 'Z' literals).  The walker
  // under test never reads this file.
  wire state = b[0];
  wire [1:0] requests = a[1:0];
  reg grant_index_w;
  reg [1:0] grant_onehot_w;
  always @(*) begin
    casez ({state, requests})
      3'b001: begin grant_onehot_w = 2'b01; grant_index_w = 1'b0; end
      3'b1?1: begin grant_onehot_w = 2'b01; grant_index_w = 1'b0; end
      3'b01?: begin grant_onehot_w = 2'b10; grant_index_w = 1'b1; end
      3'b110: begin grant_onehot_w = 2'b10; grant_index_w = 1'b1; end
      default: begin grant_onehot_w = 2'b00; grant_index_w = 1'bx; end
    endcase
  end
  reg [31:0] y_r = 32'd0;
  assign y = y_r;
  always @(posedge clk) begin
    if (reset) y_r <= 32'd0;
    else y_r <= {a[31:3], grant_index_w, grant_onehot_w};
  end
endmodule
