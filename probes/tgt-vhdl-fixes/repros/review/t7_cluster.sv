// Transitive clustering (A~B on x, B~C on y), repeat loops in two members
// (VHDL for-loop parameter "Verilog_Repeat" twice in one process), a case
// statement, a $display inside a merged member, and a fourth block on the
// same edge that shares nothing (must stay separate).
module t7_cluster;
  reg clk;
  reg [3:0] x, y, z;
  reg [1:0] i, j;
  reg [3:0] d;
  reg en;

  always_ff @(posedge clk) begin : A
    x[i] <= d[i];
  end
  always_ff @(posedge clk) begin : B
    x[j] <= ~d[j];
    repeat (2) y[i] <= d[i];
    if (en) $display("B fired at %0t i=%0d", $time, i);
  end
  always_ff @(posedge clk) begin : C
    repeat (1) y[j] <= ~d[j];
    case (i)
      2'd0: y[3] <= 1'b1;
      default: y[3] <= 1'b0;
    endcase
  end
  always_ff @(posedge clk) begin : D
    z <= x + y;   // reads pre-edge x, y; separate process
  end

  initial begin
    clk = 0; x = 4'b0000; y = 4'b0000; z = 0; d = 4'b0101; i = 0; j = 1; en = 1;
    #5 clk = 1; #5 clk = 0;
    // A: x[0] <= 1 ; B: x[1] <= ~0 = 1, y[0] <= 1 ; C: y[1] <= ~0 = 1, y[3] <= 1 ; D: z <= 0
    $display("T7a x=%b y=%b z=%b exp x=0011 y=1011 z=0000", x, y, z);
    i = 2; j = 3; en = 0;
    #5 clk = 1; #5 clk = 0;
    // A: x[2] <= 1 ; B: x[3] <= ~1 = 0, y[2] <= 1 ; C: y[3] <= ~1 = 0 and y[3] <= 0 ; D: z <= 0011 + 1011 = 1110
    $display("T7b x=%b y=%b z=%b exp x=0111 y=0111 z=1110", x, y, z);
    $finish;
  end
endmodule
