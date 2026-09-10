# VX_alu_int on sky130hd through OpenROAD — the second design for layopt

Vortex's integer ALU (`hw/rtl/core/VX_alu_int.sv`, the first target of
ASYNC-PLAN), five times gcd: 3770 cells after synthesis (nand2 639, a21oi 527,
nor2 524, o21ai 425, mux2i 204, edfxtp 151, ...). Built 2026-09-10 in
`~/src/alu-flow`:

    # flatten the SV (interfaces, packages, structs) with sv2v -- probes/alutest's recipe
    cd /usr/local/src/vortex && mkdir -p inc
    XLEN=32 python3 ci/gen_config.py --config VX_config.toml --output inc/VX_config.vh --format verilog
    XLEN=32 python3 ci/gen_config.py --config VX_types.toml  --output inc/VX_types.vh  --format verilog --resolved
    DEFS=$(cat probes/alutest/defs.txt); R=hw/rtl
    sv2v --top=alu_top $DEFS -I$R -I$R/interfaces -I$R/libs -I$R/core -I$R/fpu -Ihw/dpi -Iinc \
         $R/VX_gpu_pkg.sv $R/interfaces/VX_{execute,result,branch_ctl}_if.sv $R/libs/*.sv $R/core/VX_alu_int.sv \
         probes/alutest/alu_top.sv -w ~/src/alu-flow/alu.v
    yosys -q synth.ys                                 # -> alu_synth.v (sky130_fd_sc_hd cells)
    cd hints && openroad -exit flow_place.tcl         # -> alu_placed.def / .odb at the pre-route hand-off point
    TAG=base  openroad -exit flow_route.tcl           # -> alu_base.def (the reference routing)
    TAG=hints HINTS=$PWD/hints.tcl openroad -exit flow_route.tcl   # with layopt's placer hints

`constraint.sdc` is gcd's with a 2.0 ns clock (timing is not the point);
`flow_place.tcl` is gcd's with utilization 33 % and 2 sites of padding (4 sites
put the ALU's padded utilization at 103 %). The layopt probes take
`--name alu`: `../l4_placer_handoff.py --name alu`, `../l4_merged_cell.py --name alu`,
`../l4_gcd_whitespace.py --def ~/src/alu-flow/hints/alu_base.def`.
