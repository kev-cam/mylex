module slicecase (input clk, input [1:0] op, input [63:0] a, input [63:0] b, output reg [63:0] y);
    reg [1:0][31:0] r;
    genvar i;
    generate for (i = 0; i < 2; i = i + 1) begin : g
        always @(*) begin
            case (op)
                2'b00: r[i] = a[i*32 +: 32] & b[i*32 +: 32];
                2'b01: r[i] = a[i*32 +: 32] | b[i*32 +: 32];
                2'b10: r[i] = a[i*32 +: 32] ^ b[i*32 +: 32];
                2'b11: r[i] = a[i*32 +: 32] << b[i*32 +: 5];
            endcase
        end
    end endgenerate
    always @(posedge clk) y <= r;
endmodule
module sliceplain (input clk, input [1:0] op, input [63:0] a, input [63:0] b, output reg [63:0] y);
    reg [1:0][31:0] r;
    genvar i;
    generate for (i = 0; i < 2; i = i + 1) begin : g
        always @(*) r[i] = a[i*32 +: 32] & b[i*32 +: 32];
    end endgenerate
    always @(posedge clk) y <= r;
endmodule
module slicesingle (input clk, input [1:0] op, input [63:0] a, input [63:0] b, output reg [63:0] y);
    reg [1:0][31:0] r;
    always @(*) begin
        case (op)
            2'b00: begin r[0] = a[31:0] & b[31:0]; r[1] = a[63:32] & b[63:32]; end
            default: begin r[0] = a[31:0] | b[31:0]; r[1] = a[63:32] | b[63:32]; end
        endcase
    end
    always @(posedge clk) y <= r;
endmodule
