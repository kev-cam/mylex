// BUG 1 repro: SV reg named `pipe` collides with NVC-fork 2040 keyword `pipe`
module pipe_repro (
    input  logic clk,
    input  logic rst,
    input  logic d,
    output logic q
);
    reg pipe;
    always @(posedge clk) begin
        if (rst) pipe <= 1'b0;
        else     pipe <= d;
    end
    assign q = pipe;
endmodule
