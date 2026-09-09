# layopt placer hints: flips and abutments for the boundary dissolve (layopt/placer.py)
set __blk [ord::get_db_block]
set __i [$__blk findInst {_155_}]
$__i setOrient MY
$__i setLocation 63020 13600   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {rebuffer32}]
$__i setOrient MY
$__i setLocation 64860 13600   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {rebuffer11}]
$__i setOrient MY
$__i setLocation 35880 19040   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {_236_}]
$__i setLocation 19320 40800   ;# slide 3.220 um left to abut rebuffer12
$__i setPlacementStatus FIRM
set __i [$__blk findInst {clkbuf_2_2__f_clk}]
$__i setOrient MY
$__i setLocation 19320 51680   ;# flip N->FN, slide 4.140 um left to abut rebuffer13
$__i setPlacementStatus FIRM
set __i [$__blk findInst {rebuffer30}]
$__i setOrient MY
$__i setLocation 59800 51680   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {_162_}]
$__i setLocation 48760 57120   ;# slide 1.840 um left to abut rebuffer15
$__i setPlacementStatus FIRM
set __i [$__blk findInst {load_slew1}]
$__i setOrient R180
$__i setLocation 24380 59840   ;# flip FS->S
$__i setPlacementStatus FIRM
set __i [$__blk findInst {_113_}]
$__i setOrient MY
$__i setLocation 45080 62560   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {rebuffer28}]
$__i setOrient MY
$__i setLocation 48300 62560   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {rebuffer52}]
$__i setOrient MY
$__i setLocation 66240 62560   ;# flip N->FN
$__i setPlacementStatus FIRM
set __i [$__blk findInst {_197_}]
$__i setLocation 35420 68000   ;# slide 4.600 um left to abut rebuffer14
$__i setPlacementStatus FIRM
puts "layopt hints: 12 cells flipped or moved"
