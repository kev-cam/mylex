// prehist: the exectest oracle's pre-history (tb_exec.sv.in: `reg clk = 0; always #5 clk = ~clk`,
// reset = 1 from t0, row 0's inputs driven from t0, recorder samples 1 ns after each negedge).
// Row 0 is sampled at 11 ns, AFTER the first rising edge at 5 ns, so every recorded row k
// reflects k+1 posedges (inputs in0, in0, in1, ..., in(k-1)). A replay that compares row 0
// before any posedge (or shifts every later row by one edge) fails here on:
//   ready  -- sync-reset register that resets to 1 (VX_pipe_buffer / VX_stream_switch style):
//             the oracle already shows 1 at row 0, the un-clocked model state is 0;
//   cnt    -- declaration-initialised register (`reg [7:0] cnt_r = 5`, no reset), +1 per posedge:
//             row k reads 5 + (k+1); the model's sm_reset starts it at 5 (yosys `init` attr), so the
//             pre-history edge is what makes row 0 read 6 -- a one-edge shift is visible on EVERY row;
//   q      -- no reset, no initialiser: x before the first posedge, defined (= a) after it;
//   junk   -- no reset, no initialiser, self-dependent: x forever in the oracle (don't care).
module prehist_top(input clk, input reset, input [7:0] a,
                   output ready, output [7:0] cnt, output [7:0] q, output [7:0] junk);
    reg       ready_r;
    reg [7:0] cnt_r = 8'd5;
    reg [7:0] q_r;
    reg [7:0] junk_r;
    always @(posedge clk) begin
        if (reset) ready_r <= 1'b1; else ready_r <= a[0];
        cnt_r  <= cnt_r + 8'd1;
        q_r    <= a;
        junk_r <= junk_r + 8'd1;
    end
    assign ready = ready_r;
    assign cnt   = cnt_r;
    assign q     = q_r;
    assign junk  = junk_r;
endmodule
