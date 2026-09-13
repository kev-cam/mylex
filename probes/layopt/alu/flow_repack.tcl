# layopt: the placer re-packs the dissolved placement -- merged cells are PLACED standard cells
# (widths rounded up to sites); detailed placement legalises and packs, mirroring is re-optimised,
# free sites per row are counted before and after, then the result is routed.
set P /home/claude/tools/orfs-sky130hd
set D /home/claude/src/alu-flow/hints
read_lef $P/sky130_fd_sc_hd.tlef
read_lef $P/sky130_fd_sc_hd_merged.lef
read_lef $D/merged.lef
read_def $D/merged.def
proc layopt_free_sites {tag} {
    set blk [ord::get_db_block]
    set total 0
    foreach row [$blk getRows] {
        set bb [$row getBBox]
        set rx0 [$bb xMin]; set rx1 [$bb xMax]; set ry0 [$bb yMin]
        set occ 0
        foreach inst [$blk getInsts] {
            set ib [$inst getBBox]
            if {[$ib yMin] == $ry0 && [$ib xMin] >= $rx0 && [$ib xMax] <= $rx1} {
                set occ [expr {$occ + [$ib xMax] - [$ib xMin]}]
            }
        }
        set total [expr {$total + $rx1 - $rx0 - $occ}]
    }
    set site [[[lindex [$blk getRows] 0] getSite] getWidth]
    puts "layopt free sites $tag: [expr {$total / $site}] sites = [expr {$total / 1000.0}] um"
}
layopt_free_sites before
detailed_placement
optimize_mirroring
check_placement -verbose
layopt_free_sites after
write_def $D/alu_repacked.def
set_routing_layers -signal met1-met5 -clock met3-met5
global_route -congestion_iterations 30 -verbose
detailed_route -output_drc $D/route_drc_repack.rpt -verbose 1
write_def $D/alu_repack_routed.def
exit
