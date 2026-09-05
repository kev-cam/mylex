module r7_sra (
  input clk,
  input reset,
  input [31:0] a,
  input [31:0] b,
  input [3:0] op,
  output [31:0] y
);
  // Verilog twin of r7_sra.vhd for the accel's TEXT path (vhdl2vlog has no
  // l3d_sra; the real ALU's text path synthesises alu.v's
  // `$signed(shr_in1) >>> imm`).  The walker under test never reads this.
  wire tmp_ivl_2 = op[0] & a[31];
  wire [32:0] shr_in1 = {tmp_ivl_2, a};
  wire [31:0] y_c = $signed(shr_in1) >>> b[4:0];
  reg [31:0] y_r = 32'd0;
  always @(posedge clk) begin
    if (reset) y_r <= 32'd0;
    else y_r <= y_c;
  end
  assign y = y_r;
endmodule
