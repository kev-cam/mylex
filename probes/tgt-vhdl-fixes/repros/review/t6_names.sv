// BUG-1: identifiers that are keywords in VHDL-2008/2019/NVC/the fork but
// legal SV identifiers, in every name position the translator emits.
module pipe #(parameter VIEW = 1, parameter PIPE = 2) (
  input  wire view,
  input  wire [PIPE-1:0] vpkg,
  output reg  private_o,
  output reg  reverse_range
);
  localparam FAIRNESS = 3;
  reg [1:0] vprop;
  reg [FAIRNESS-1:0] vunit;
  always @* begin
    vprop = vpkg;
    vunit = {view, vpkg};
    private_o = vprop[VIEW - 1];
    reverse_range = vunit[0];
  end
endmodule

module t6_names;
  reg view, private;
  reg [1:0] vpkg;
  wire private_w, rr;
  pipe vmode (.view(view), .vpkg(vpkg), .private_o(private_w), .reverse_range(rr));
  initial begin
    view = 1; vpkg = 2'b10; private = 0;
    #1 $display("T6 private_w=%b rr=%b exp=1 1", private_w, rr);
    $finish;
  end
endmodule
