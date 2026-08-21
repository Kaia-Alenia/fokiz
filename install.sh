#!/usr/bin/env bash
# Fokiz — Install script via curl
# Copyright (C) Alenia Studios — GNU GPL v3
# Usage: curl -sSL https://raw.githubusercontent.com/Kaia-Alenia/fokiz/main/install.sh | bash

set -e

REPO_URL="https://github.com/Kaia-Alenia/fokiz.git"
INSTALL_DIR="$HOME/.local/share/fokiz"

echo "============================================================"
echo "  Fokiz — Ulysses Contract CLI"
echo "============================================================"
echo

# 1. Check prerequisites
echo "[1/4] Checking prerequisites..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but not installed." >&2
    exit 1
fi
if ! command -v git >/dev/null 2>&1; then
    echo "Error: git is required but not installed." >&2
    exit 1
fi
if ! systemctl --user is-system-running --quiet >/dev/null 2>&1; then
    echo "Warning: systemd --user does not seem to be running. The monitor timer may not start automatically." >&2
fi

# 2. Clone or update repository
echo "[2/4] Fetching Fokiz from GitHub..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  -> Directory $INSTALL_DIR already exists. Updating..."
    cd "$INSTALL_DIR"
    git fetch origin main
    git reset --hard origin/main
elif [ -d "$INSTALL_DIR" ]; then
    echo "  -> Directory $INSTALL_DIR exists but is not a git repository. Re-cloning..."
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
else
    echo "  -> Cloning to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Run the Python installer
echo "[3/4] Running Python installer..."
python3 install.py

# 4. Clean up Git history (optional, to save space, but we keep it for easy updates)
# rm -rf "$INSTALL_DIR/.git"

echo
echo "============================================================"
echo "  Installation Complete!"
echo "============================================================"
echo "Make sure ~/.local/bin is in your PATH."
echo "Run 'fokiz init' to start using Fokiz."
echo "============================================================"
