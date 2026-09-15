#!/bin/bash
# build_openroad.sh — NON-ROOT OpenROAD common-deps + build (run as claude).
#   run as:   bash /home/claude/tools/build_openroad.sh
#
# Prereq: `sudo bash install_layout_root.sh` has installed the -base apt
# packages (build-essential, qt5 dev, tcl-dev, libpcre2-dev, ...). Without them
# the from-source dep builds below fail.
#
# Why -local (not root, not /usr/local):
#   DependencyInstaller.sh -common installs a REAL CMake 3.31.9 first, then the
#   from-source deps (swig, boost, eigen, lemon, spdlog, gtest, abseil, or-tools).
#   With -local everything lands in ~/.local. ~/.local/bin precedes
#   /usr/local/bin in PATH, so `cmake` resolves to the real one and the smak
#   shim at /usr/local/bin/cmake is bypassed AND left intact. -local also
#   forbids root (the script errors under sudo), which is exactly what we want.
set -euo pipefail
DEST=/home/claude/tools/OpenROAD
DEPS_FILE="$DEST/etc/openroad_deps_prefixes.txt"

command -v cmake >/dev/null && echo "cmake in PATH: $(command -v cmake) ($(cmake --version | head -1))"

echo "== 1/2  common deps -> ~/.local  (DependencyInstaller.sh -common -local)"
bash "$DEST/etc/DependencyInstaller.sh" -common -local

echo "== 2/2  build OpenROAD  (Build.sh -local, ~/.local prefixes)"
BUILD_ARGS=(-local)
[ -f "$DEPS_FILE" ] && BUILD_ARGS+=("-deps-prefixes-file=$DEPS_FILE")
bash "$DEST/etc/Build.sh" "${BUILD_ARGS[@]}"

echo
BIN="$DEST/build/src/openroad"
if [ -x "$BIN" ]; then
    echo "BUILT: $BIN"
    "$BIN" -version || true
else
    echo "Build finished but $BIN not found — check Build.sh output above."
fi
