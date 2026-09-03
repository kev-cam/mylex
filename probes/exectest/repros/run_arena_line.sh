#!/bin/bash
export PATH=/usr/local/src/nvc/build/bin:$PATH NVC_LIBPATH=/usr/local/src/nvc/build/lib
# every function is compiled on its first call, so readline/grow/shrink/consume run
# as native code (allocating through __nvc_mspace_alloc) from the first line;
# unfixed fork: "line corrupted" / SIGSEGV, fixed: PASS
export NVC_JIT_THRESHOLD=${NVC_JIT_THRESHOLD:-1}
d=$(dirname $(readlink -f $0)); cd $d
[ -f arena_new.txt ] || python3 -c "open('arena_new.txt','w').write(''.join(chr(97 + i % 26) * 200 + chr(10) for i in range(400)))"
rm -rf work_arena_line; mkdir -p work_arena_line; cp arena_new.txt work_arena_line/
cd work_arena_line && nvc --std=2040 -a ../arena_line.vhd && nvc --std=2040 -e arena_line && nvc --std=2040 -r arena_line
