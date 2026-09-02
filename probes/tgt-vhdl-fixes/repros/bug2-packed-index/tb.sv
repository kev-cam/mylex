module tb;
  reg clk = 0, reset = 1;
  reg [1:0] data_in = 2'b00;
  wire [1:0] data_out;
  repro #(.DATAW(2), .RESETW(1), .DEPTH(1)) dut(.clk(clk), .reset(reset), .data_in(data_in), .data_out(data_out));
  initial begin
    #1 clk = 1; #1 clk = 0;
    $display("after reset: data_out=%b (expect 1x)", data_out);
    reset = 0; data_in = 2'b01;
    #1 clk = 1; #1 clk = 0;
    $display("after load : data_out=%b (expect 01)", data_out);
    $finish;
  end
endmodule
