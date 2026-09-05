module r3_nba (
  input clk,
  input reset,
  input [31:0] a,
  input [31:0] b,
  input [3:0] op,
  output [31:0] y
);
  // Verilog twin of r3_nba.vhd for the accel's TEXT path (the tgt-vhdl flow
  // always carries the original Verilog behind nvc_verilog_src; vhdl2vlog
  // itself cannot emit the merged second `if rising_edge`).  The walker
  // under test never reads this file.
  reg [31:0] pipe_sig = 32'd0;
  assign y = pipe_sig;
  always @(posedge clk) begin
    if (reset) pipe_sig[31] <= 1'b0;
    else if (op[0]) pipe_sig[31] <= a[31];
  end
  always @(posedge clk) begin
    if (op[0]) pipe_sig[30:0] <= a[30:0] ^ b[30:0];
  end
endmodule
