// Repro: per-lane `always @*` blocks each write a constant slice of one reg,
// then a sub-slice of it (VX_lsu_slice g_mem_req_data). Each lane's process
// keeps direct slice assignments, so together they drive disjoint bits --
// legal VHDL, correct result. The multi-writer census called the mixed
// constant slices a whole-signal write and warned that one lane would
// clobber the other. Self-checking TB: tb_combslices.vhd.
module top(input [63:0] d, input [3:0] align, output [63:0] q);
  reg [63:0] data;
  genvar i;
  for (i = 0; i < 2; i = i + 1) begin : g_lane
    always @(*) begin
      data[i*32 +: 32] = d[i*32 +: 32];
      case (align[i*2 +: 2])
        1: data[i*32+31 -: 24] = d[i*32+23 -: 24];
        2: data[i*32+31 -: 16] = d[i*32+15 -: 16];
        3: data[i*32+31 -: 8]  = d[i*32+7  -: 8];
        default: ;
      endcase
    end
  end
  assign q = data;
endmodule
