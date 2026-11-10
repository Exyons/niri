#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
cargo test --release --locked -p niri -p niri-config -p niri-ipc
cargo build --release --locked -p niri
target/release/niri --version
target/release/niri validate
