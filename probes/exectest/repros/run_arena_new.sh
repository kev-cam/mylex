#!/bin/bash
# usage: ./run_arena_new.sh   -- analyse/elaborate/run the NVC eval-arena repro in ./work_arena_new
export PATH=/usr/local/src/nvc/build/bin:$PATH NVC_LIBPATH=/usr/local/src/nvc/build/lib
# every function is compiled on its first call, so readline/grow/shrink/consume run
# as native code (allocating through __nvc_mspace_alloc) from the first line;
# unfixed fork: "line corrupted" / SIGSEGV, fixed: PASS
export NVC_JIT_THRESHOLD=${NVC_JIT_THRESHOLD:-1}
d=$(dirname $(readlink -f $0)); cd $d
[ -f arena_new.txt ] || python3 -c "open('arena_new.txt','w').write(''.join(chr(97 + i % 26) * 200 + chr(10) for i in range(400)))"
rm -rf work_arena_new; mkdir -p work_arena_new; cp arena_new.txt work_arena_new/
cd work_arena_new && nvc --std=2040 -a ../arena_new.vhd && nvc --std=2040 -e arena_new && nvc --std=2040 -r arena_new
