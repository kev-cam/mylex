module r4_slice_arm (
  input clk,
  input reset,
  input [31:0] a,
  input [31:0] b,
  input [3:0] op,
  output [31:0] y
);
  // Verilog twin of r4_slice_arm.vhd for the accel's TEXT path (vhdl2vlog
  // has no l3d_shcount).  The walker under test never reads this file.
  reg [63:0] msc_result;
  always @* begin
    case (op[1:0])
      2'b00: msc_result[31:0] = a & b;
      2'b01: msc_result[31:0] = a | b;
      2'b10: msc_result[31:0] = a ^ b;
      2'b11: msc_result[31:0] = a << b[4:0];
    endcase
  end
  always @* begin
    case (op[3:2])
      2'b00: msc_result[63:32] = b & a;
      2'b01: msc_result[63:32] = b | a;
      2'b10: msc_result[63:32] = b ^ a;
      2'b11: msc_result[63:32] = b << a[4:0];
    endcase
  end
  wire [31:0] y_c = msc_result[63:32] ^ msc_result[31:0];
  reg [31:0] y_r = 32'd0;
  always @(posedge clk) begin
    if (reset) y_r <= 32'd0;
    else y_r <= y_c;
  end
  assign y = y_r;
endmodule
