// Newly reserved words that are legal SV identifiers, as module, port (mixed case) and reg names.
// (context/force/release/parameter/default/cover/property/sequence/strong/restrict/assume/protected
//  are SV keywords themselves so cannot appear in SV source.)
module pipe (                          // module named after the keyword -> entity rename
    input  logic clk,
    input  logic PIPE,                 // port, mixed case (VHDL is case-insensitive)
    input  logic view,                 // VHDL-2019 keyword as port
    output logic private,              // VHDL-2019 keyword as output port
    output logic [3:0] vunit           // 2008 PSL word as output port
);
    reg reverse_range, fairness, restrict_guarantee, assume_guarantee, vmode, vprop, vpkg;
    always @(posedge clk) begin
        reverse_range <= PIPE; fairness <= view; restrict_guarantee <= reverse_range;
        assume_guarantee <= fairness; vmode <= restrict_guarantee; vprop <= assume_guarantee;
        vpkg <= vmode;
    end
    assign private = vpkg;
    assign vunit = {vprop, vmode, fairness, reverse_range};
endmodule
