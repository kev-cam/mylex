// Merge-pass on an unpacked memory with two same-edge writers and a reset
// branch in only one of them (reset priority across merged blocks).
module t2_mem;
  reg clk, rst;
  reg [3:0] mem [0:3];
  reg [1:0] wa, wb;
  reg [3:0] da, db;
  reg wen_a, wen_b;
  reg [3:0] rd;
  reg [1:0] ra;

  always_ff @(posedge clk) begin
    if (rst) begin
      mem[0] <= 4'd0; mem[1] <= 4'd0; mem[2] <= 4'd0; mem[3] <= 4'd0;
    end else if (wen_a)
      mem[wa] <= da;
  end
  always_ff @(posedge clk) if (wen_b) mem[wb] <= db;
  // read-side block (same edge, different reg) -- must NOT be clustered with
  // the writers (shares no written signal) and reads pre-edge mem.
  always_ff @(posedge clk) rd <= mem[ra];

  initial begin
    clk = 0; rst = 1; wen_a = 0; wen_b = 0; wa = 0; wb = 0; da = 0; db = 0; ra = 0;
    #5 clk = 1; #5 clk = 0;
    $display("T2a mem=%h %h %h %h rd=%h exp=0 0 0 0 rd=x", mem[0], mem[1], mem[2], mem[3], rd);
    rst = 0; wen_a = 1; wa = 1; da = 4'hA; wen_b = 1; wb = 2; db = 4'hB; ra = 1;
    #5 clk = 1; #5 clk = 0;
    $display("T2b mem=%h %h %h %h rd=%h exp=0 a b 0 rd=0", mem[0], mem[1], mem[2], mem[3], rd);
    wen_a = 0; wb = 3; db = 4'hC; ra = 2;
    #5 clk = 1; #5 clk = 0;
    $display("T2c mem=%h %h %h %h rd=%h exp=0 a b c rd=b", mem[0], mem[1], mem[2], mem[3], rd);
    rst = 1; wen_b = 0; ra = 3;
    #5 clk = 1; #5 clk = 0;
    $display("T2d mem=%h %h %h %h rd=%h exp=0 0 0 0 rd=c", mem[0], mem[1], mem[2], mem[3], rd);
    $finish;
  end
endmodule
