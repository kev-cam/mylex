// Merge-pass shape tests (translation + nvc analysis only).
module shapes (
    input  logic       clk, rst, clk2, en,
    input  logic [3:0] d,
    output logic [3:0] q,      // async-reset template, two blocks
    output logic [3:0] r,      // different sensitivities -> warning, no merge
    output logic [3:0] s,      // colliding locals of different types -> rename
    output logic [3:0] t       // blocking temp shared by both blocks
);
    // (1) async-reset template (posedge clk or posedge rst) in both blocks
    always_ff @(posedge clk or posedge rst) begin
        if (rst) q[3:2] <= 2'b00;
        else if (en) for (int i = 2; i < 4; i++) q[i] <= d[i];
    end
    always_ff @(posedge clk or posedge rst) begin
        if (rst) q[1:0] <= 2'b00;
        else if (en) for (int i = 0; i < 2; i++) q[i] <= d[i];
    end
    // (2) different clocks writing one reg (cannot merge)
    always_ff @(posedge clk)  for (int i = 2; i < 4; i++) r[i] <= d[i];
    always_ff @(posedge clk2) for (int i = 0; i < 2; i++) r[i] <= d[i];
    // (3) same-name locals with different types
    always_ff @(posedge clk) begin
        for (int i = 2; i < 4; i++) s[i] <= d[i];
    end
    always_ff @(posedge clk) begin
        for (byte i = 0; i < 2; i++) s[i] <= d[i];
    end
    // (4) blocking temp in both blocks
    logic [3:0] tmp;
    always_ff @(posedge clk) begin
        tmp = d & 4'hC;
        for (int i = 2; i < 4; i++) t[i] <= tmp[i];
    end
    always_ff @(posedge clk) begin
        tmp = d & 4'h3;
        for (int i = 0; i < 2; i++) t[i] <= tmp[i];
    end
endmodule
