// Repro: arithmetic whose Verilog context width is ONE bit. VX_lane_dispatch
// has `wire [0:0] warp_pid = block_pid[i+:1] + 1'(sid * N)` and
// `ISSUE_W'(batch_idx * BLOCK_SIZE) + ISSUE_W'(block_idx)` with ISSUE_W = 1.
// Both operands translate to scalar logic3d, a SUBTYPE OF NATURAL, so the
// emitted VHDL `a + b` resolved to the predefined integer "+" on the 3-bit
// encodings: L3D_0 + L3D_0 = 2 + 2 = 4 = L3D_Z. In VX_execute that Z became
// x in every execute header pid (commit_if sid, the LSU client tag).
// Covers the LPM (continuous) and expression (procedural) paths for + - *,
// and / mod on the LPM path.
// Self-check: tb_add1bit.vhd (all four input pairs; x operands).
module top(input a, input b,
           output [0:0] s, output [0:0] d, output [0:0] m, output [0:0] q, output [0:0] r,
           output reg [0:0] ps, output reg [0:0] pd, output reg [0:0] pm);
  wire [0:0] wa = a, wb = b;
  assign s = wa + wb;      // LPM_ADD, width 1
  assign d = wa - wb;      // LPM_SUB, width 1
  assign m = wa * wb;      // LPM_MULT, width 1
  assign q = wa / wb;      // LPM_DIVIDE, width 1
  assign r = wa % wb;      // LPM_MOD, width 1
  always @* begin          // expression path
    ps = wa + wb;
    pd = wa - wb;
    pm = wa * wb;
  end
endmodule
