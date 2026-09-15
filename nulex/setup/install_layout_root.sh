#!/bin/bash
# install_layout_root.sh — the ONLY root/sudo steps for the layout toolchain.
#   run as:   sudo bash /home/claude/tools/install_layout_root.sh
#
# Already done WITHOUT root (claude session): sky130 PDK (volare ->
# ~/tools/pdk/sky130A, wired into ~/tools/sky130_fd_sc_hd) and Xyce
# (/usr/local/bin/Xyce). This script installs ONLY the privileged pieces:
#   1. clone OpenROAD (as claude, so the tree stays user-owned)
#   2. OpenROAD *base* apt packages   (DependencyInstaller.sh -base)
#   3. KLayout (optional)
#
# IMPORTANT — it deliberately runs `-base`, NOT `-all`/`-common`:
#   * `-base` only apt-installs system libraries. It does NOT touch cmake.
#   * `-all`/`-common` as root would install CMake 3.31.9 with
#     --prefix=/usr/local, CLOBBERING the smak cmake shim at
#     /usr/local/bin/cmake (a symlink -> /usr/local/share/smak/cmake) and
#     routing every dep build through smak's interpreter. Forbidden.
#   The from-source common deps + the OpenROAD build are non-root and land in
#   ~/.local (which precedes /usr/local in PATH, so a real cmake shadows the
#   shim); the claude session runs build_openroad.sh for that afterwards.
#
# NOTE: a bare `DependencyInstaller.sh` with no flag ERRORS OUT
# ("You must use one of: -all, -base, ...") — that was the earlier failure.
set -euo pipefail
USER_NAME=claude
DEST=/home/claude/tools/OpenROAD

echo "== 1/3  clone OpenROAD (as $USER_NAME, user-owned tree)"
if [ ! -d "$DEST/.git" ]; then
    sudo -u "$USER_NAME" git clone --recursive \
        https://github.com/The-OpenROAD-Project/OpenROAD.git "$DEST"
else
    echo "   $DEST already cloned — skipping"
fi

echo "== 2/3  OpenROAD BASE apt packages  (DependencyInstaller.sh -base)"
bash "$DEST/etc/DependencyInstaller.sh" -base || {
    echo "!! DependencyInstaller -base failed; see output above"; exit 1; }

echo "== 3/3  KLayout (optional signoff DRC/extract; layopt has its own)"
apt-get update -y && apt-get install -y klayout || \
    echo "   (klayout apt install failed — optional, continuing)"

chown -R "$USER_NAME":"$USER_NAME" "$DEST" 2>/dev/null || true
echo
echo "ROOT STEPS DONE. Next, as $USER_NAME (NO sudo) — the claude session runs:"
echo "   bash /home/claude/tools/build_openroad.sh"
echo "   (-> DependencyInstaller.sh -common -local  then  Build.sh -local)"
