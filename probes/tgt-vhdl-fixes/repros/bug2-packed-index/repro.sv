// BUG 2 repro: 2-D packed reg, variable outer index + constant inner part-select.
module repro #(
    parameter DATAW  = 2,
    parameter RESETW = 1,
    parameter DEPTH  = 1
) (
    input wire clk,
    input wire reset,
    input wire [DATAW-1:0] data_in,
    output wire [DATAW-1:0] data_out
);
    reg [DEPTH-1:0][DATAW-1:0] pipe;

    always_ff @(posedge clk) begin
        if (reset) begin
            // variable outer index, constant inner part-select
            for (int i = 0; i < DEPTH; ++i)
                pipe[i][DATAW-1 : DATAW-RESETW] <= 1'b1;
        end else begin
            // constant outer index control case
            pipe[0][DATAW-1 : DATAW-RESETW] <= data_in[DATAW-1 : DATAW-RESETW];
            // variable outer index, low-part control case (base 0 within word)
            for (int i = 0; i < DEPTH; ++i)
                pipe[i][DATAW-RESETW-1 : 0] <= data_in[DATAW-RESETW-1 : 0];
        end
    end

    assign data_out = pipe[DEPTH-1];
endmodule
