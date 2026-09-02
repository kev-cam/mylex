// Merge-pass semantic cases beyond the minimal repro. Each output is checked
// by tb_merge_cases.vhd against SystemVerilog NBA semantics.
module merge_cases (
    input  logic       clk,
    input  logic       reset,
    input  logic       en,
    input  logic [3:0] d,
    output logic [3:0] cap,     // (1) same-named persistent block-locals in two merged blocks
    output logic [3:0] same,    // (2) same static bit from two blocks: source order wins
    output logic [3:0] both,    // (3) opposite edges of one clock, dynamic index in both
    output logic [3:0] single   // (4) single writer: must be untouched by the pass
);
    // (1) Block A and block B each declare a STATIC block-scope `cnt` of the
    //     same type and keep state in it across cycles (A counts up from 0,
    //     B counts down from 3). Both write `cap` on posedge clk -> merged.
    //     The two `cnt`s must stay distinct variables after the merge.
    always_ff @(posedge clk) begin : blkA
        logic [1:0] cnt;
        for (int i = 2; i < 4; i++) cap[i] <= cnt[i-2];
        if (reset) cnt = 2'd0; else cnt = cnt + 2'd1;
    end
    always_ff @(posedge clk) begin : blkB
        logic [1:0] cnt;
        for (int i = 0; i < 2; i++) cap[i] <= cnt[i];
        if (reset) cnt = 2'd3; else cnt = cnt - 2'd1;
    end

    // (2) Two blocks write the SAME bit same[0] every cycle (a Verilog race);
    //     the merged process fixes source order: block E (later) wins.
    always_ff @(posedge clk) begin : blkD
        for (int i = 0; i < 1; i++) same[i] <= 1'b0;
        same[3:1] <= d[3:1];
    end
    always_ff @(posedge clk) begin : blkE
        for (int i = 0; i < 1; i++) same[i] <= 1'b1;
    end

    // (3) Opposite edges of one clock, both dynamic index -> same sensitivity
    //     set {clk} -> merged; each body keeps its own edge guard.
    always_ff @(posedge clk) begin : blkF
        for (int i = 2; i < 4; i++) both[i] <= d[i];
    end
    always_ff @(negedge clk) begin : blkG
        for (int i = 0; i < 2; i++) both[i] <= d[i];
    end

    // (4) Single writer with a dynamic index (whole-signal shadow, one process).
    always_ff @(posedge clk) begin : blkH
        if (reset) single <= 4'b0000;
        else if (en) for (int i = 0; i < 4; i++) single[i] <= d[3-i];
    end
endmodule
