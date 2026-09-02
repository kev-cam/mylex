// Shapes for promote_wait_until_edge_form (process.cc): always blocks that
// iverilog's tgt-vhdl draws in the `wait until <edge>` form because they
// read a blocking temporary, and their neighbours.
//  P1  blocking temp + async reset (the async-reset template gives up on the
//      wait-for-0 body, so this takes the generic wait-until form) merged
//      with a template-form block on the same reg
//  P2  blocking temp + a real `#1` delay: must NOT be promoted (keeps the
//      wait-until form; still simulates)
//  P3  event control that is not the top statement: not promoted
//  P4  negedge + blocking temp, merged with a plain negedge block
//  P5  conditional blocking write, temp held across activations
//  P6  blocking temp read in the loop condition (wait-for-0 inside a loop)
module t10_promote;
  reg clk, rst, c;
  reg [3:0] d;
  reg [3:0] a, t1;          // P1 : a[1:0] from a template block, a[3:2] via temp
  reg [3:0] b, t2;          // P2
  reg [3:0] e, t3;          // P3
  reg [3:0] f, t4;          // P4
  reg [3:0] g, t5;          // P5
  reg [3:0] h, t6;          // P6
  integer k;

  // P1
  always_ff @(posedge clk or posedge rst)
    if (rst) a[1:0] <= 2'b00; else a[1:0] <= d[1:0];
  always_ff @(posedge clk or posedge rst)
    if (rst) a[3:2] <= 2'b00;
    else begin t1 = d ^ 4'hF; a[3:2] <= t1[3:2]; end

  // P2
  always @(posedge clk) begin t2 = d + 1; #1 b <= t2; end

  // P3
  always begin @(posedge clk); t3 = d - 1; e <= t3; end

  // P4
  always_ff @(negedge clk) f[1:0] <= d[1:0];
  always_ff @(negedge clk) begin t4 = ~d; f[3:2] <= t4[3:2]; end

  // P5
  always_ff @(posedge clk) begin if (c) t5 = d; g <= t5; end

  // P6
  always_ff @(posedge clk) begin
    t6 = 0;
    for (k = 0; k < 4; k = k + 1) begin
      if (t6 < d) t6 = t6 + 1;
    end
    h <= t6;
  end

  initial begin
    clk = 0; rst = 1; c = 1; d = 4'b0101; t5 = 4'hF;
    a = 0; b = 0; e = 0; f = 0; g = 0; h = 0;
    #5 rst = 0;
    #5 clk = 1; #5 clk = 0; #1;
    $display("T10a a=%b b=%b e=%b f=%b g=%b h=%b", a, b, e, f, g, h);
    // a: [1:0]=01 [3:2]=~0101[3:2]=10 -> 1001 ; b: 0110 (at 11) ; e: 0100
    // f: negedge at 15: [1:0]=01 [3:2]=~d[3:2]=10 -> 1001 ; g: d=0101 ; h: min(4,d)=4 -> 0100
    d = 4'b0011; c = 0;
    #5 clk = 1; #5 clk = 0; #1;
    $display("T10b a=%b b=%b e=%b f=%b g=%b h=%b", a, b, e, f, g, h);
    // a: 0011|~0011[3:2]=11 -> 1111 ; b: 0100 ; e: 0010 ; f: 11|11 -> 1111
    // g: c=0 -> t5 held = 0101 ; h: min(4,3)=3 -> 0011
    rst = 1; #1;
    $display("T10c a=%b (async reset -> 0000)", a);
    $finish;
  end
endmodule
