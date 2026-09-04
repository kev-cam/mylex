module r11_oob (
  input clk,
  input reset,
  input [31:0] a,
  input [31:0] b,
  input [3:0] op,
  output [31:0] y
);
  // Verilog twin of r11_oob.vhd for the accel's TEXT path (the tgt-vhdl flow
  // always carries the original Verilog behind nvc_verilog_src; vhdl2vlog's
  // rendering of the unrolled OOB_WriteV loops sends yosys into a multi-
  // minute proc_dlatch run).  The walker under test never reads this file.
  reg [31:0] result_out_data;
  reg [31:0] packed;
  integer i;
  always @(*) begin
    for (i = 0; i < 1; i = i + 1)
      result_out_data[i * 32 +: 32] = 32'bx;
    for (i = 0; i < 1; i = i + 1)
      result_out_data[op[0] * 32 +: 32] = a[i * 32 +: 32];
  end
  always @(*) begin
    packed = 32'd0;
    packed[op[2:1] * 8 +: 8] = b[7:0];
  end
  reg [31:0] y_r = 32'd0;
  assign y = y_r;
  always @(posedge clk) begin
    if (reset) y_r <= 32'd0;
    else y_r <= result_out_data ^ packed;
  end
endmodule
