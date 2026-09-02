// Minimal repro for BUG 3: two always_ff blocks on the same posedge write
// DISJOINT bits of one 2-bit reg. Each write uses a loop-variable index so
// tgt-vhdl's nba_defer_commits() cannot prove a static slice and falls back
// to a WHOLE-signal shadow (`v := q; ...; wait for 0 ns; q <= v;`) in BOTH
// processes -- two drivers each re-asserting a stale copy of the other's bit.
// This is exactly the VX_pipe_register g_partial_reset idiom (block A owns
// the reset-able valid bit, block B owns the data bit), minus the 2-D packed
// array so BUG 2 (flat-index mis-lowering) and BUG 1 (`pipe` keyword) stay
// out of the picture.
module nba_slice (
    input  logic       clk,
    input  logic       reset,
    input  logic       en,
    input  logic [1:0] d,
    output logic [1:0] q
);
    // block A: owns q[1] (valid-style bit): reset, else enable
    always_ff @(posedge clk) begin
        if (reset) begin
            for (int i = 0; i < 1; ++i) q[i+1] <= 1'b0;
        end else if (en) begin
            for (int i = 0; i < 1; ++i) q[i+1] <= d[i+1];
        end
    end

    // block B: owns q[0] (data-style bit): enable only
    always_ff @(posedge clk) begin
        if (en) begin
            for (int i = 0; i < 1; ++i) q[i] <= d[i];
        end
    end
endmodule
