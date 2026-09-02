// Control: names that must NOT be renamed (not reserved, or reserved word only as a substring)
module control (
    input  logic clk,
    input  logic pipeline,     // contains "pipe" as prefix
    input  logic my_pipe,      // contains "pipe" as suffix
    output logic pipes         // prefix + extra char
);
    reg piped;
    reg pipe_reg;
    reg viewport;
    reg privates;
    reg data;
    always @(posedge clk) begin
        piped    <= pipeline;
        pipe_reg <= my_pipe;
        viewport <= piped;
        privates <= pipe_reg;
        data     <= viewport ^ privates;
    end
    assign pipes = data;
endmodule
