# project-aegis

Portfolio ground-robotics project with Python perception/verification and a Rust control crate. Treat it as simulation-first unless hardware evidence proves a stronger state.

## Start here

1. Read `README.md`, `configs/default.yaml`, and the relevant safety/operations docs.
2. Keep `simulation_mode: true` by default.
3. Inspect the dirty worktree before editing.

## Commands

```bash
python3 -m pip install -e '.[dev]'
maturin develop -m crates/aegis-control/Cargo.toml
PYTHONPATH=src pytest
cargo test --manifest-path crates/aegis-control/Cargo.toml
```

## Safety and claims

- Never enable motor output, change GPIO mappings, or run hardware-control commands without explicit user authorization and a verified emergency-stop path.
- A passing simulation or unit test is not a hardware test or field validation.
- Preserve the temporal-verification boundary: a single detection must not directly trigger behavior.
- Do not add targeting, weapons, autonomous mission expansion, or consequential-action authority.
- Keep credentials and local telemetry containing sensitive data out of version control.
