#!/bin/bash
# install_layout_root.sh — the ONLY root/sudo steps for the layout toolchain.
#   run as:   sudo bash /home/claude/tools/install_layout_root.sh
#
# What's already done WITHOUT root (by the claude session): the sky130 PDK
# (volare -> ~/tools/pdk/sky130A, wired into ~/tools/sky130_fd_sc_hd) and Xyce
# (already built at /usr/local/bin/Xyce). This script only installs the pieces
# that need apt/root: OpenROAD's system build-dependencies, and (optional)
# KLayout. It does NOT build OpenROAD — that step is non-root and the claude
# session runs it afterwards (etc/Build.sh).
set -euo pipefail
USER_NAME=claude
DEST=/home/claude/tools/OpenROAD

echo "== 1/3  clone OpenROAD (as $USER_NAME, so the build tree stays user-owned)"
if [ ! -d "$DEST/.git" ]; then
    sudo -u "$USER_NAME" git clone --recursive \
        https://github.com/The-OpenROAD-Project/OpenROAD.git "$DEST"
else
    echo "   $DEST already cloned — skipping"
fi

echo "== 2/3  OpenROAD system build-dependencies (apt, root)"
# OpenROAD ships its own dependency installer; -base=all installs runtime+build pkgs.
"$DEST/etc/DependencyInstaller.sh" || {
    echo "!! DependencyInstaller failed; see its output above"; exit 1; }

echo "== 3/3  KLayout (optional signoff extraction/DRC oracle)"
apt-get update -y && apt-get install -y klayout || \
    echo "   (klayout apt install failed — optional; layopt has its own extractor)"

chown -R "$USER_NAME":"$USER_NAME" "$DEST" 2>/dev/null || true
echo
echo "ROOT STEPS DONE. Next, as $USER_NAME (NO sudo):"
echo "   $DEST/etc/Build.sh          # builds openroad (~30-60 min) -> $DEST/build/src/openroad"
echo "   # the claude session will run this and wire it into the layopt flow."
