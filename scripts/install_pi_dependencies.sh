#!/usr/bin/env bash
# Install AEGIS dependencies on a Raspberry Pi 5 (Ubuntu Server 24.04 LTS).
set -euo pipefail

echo "[aegis] updating apt..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv libgl1 libglib2.0-0

# Rust toolchain — required to build the aegis-control crate (motor + safety layer).
if ! command -v cargo >/dev/null 2>&1; then
    echo "[aegis] installing Rust toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[aegis] creating virtualenv..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "[aegis] installing aegis with hardware extras..."
pip install --upgrade pip
pip install -e ".[hardware,dev]"

echo "[aegis] building Rust motor extension (with hardware GPIO feature)..."
maturin develop --release -m crates/aegis-control/Cargo.toml --features hardware

echo "[aegis] done. Activate with: source .venv/bin/activate"
