# Firmware data dictionaries

Klipper's batch mode needs each MCU's data dictionary (the commands and pins its firmware offers) in place of a live board. These are committed so the offline tests run without building firmware (axis-expansion addendum D44).

| Dictionary | MCU in the config | Board | Kconfig (here) | Copied from |
|---|---|---|---|---|
| `m8p.dict` | `[mcu]` | Manta M8P V2.0, STM32H723, over USB | `m8p.config` | cb1-autopipette `config/klipper-manta-mcu.config` (`mantaFirmware`) |
| `octopus.dict` | `[mcu octopus]` | Octopus V1.1, STM32F446, over USB | `octopus.config` | cb1-autopipette `config/klipper-octopus-mcu.config`, the same as the plan's `reference/firmware/octopus-v1.1-f446.config` (CB1-1) |
| `host.dict` | `[mcu CB1]` | Linux host process | `host.config` | cb1-autopipette `config/klipper-host-mcu.config` |

- **Klipper rev:** `7bc4d09465d31cd30fc0822e8d0abe02cc8c547f` (nixpkgs `klipper` 0.13.0-unstable-2026-09-28, via cb1-autopipette's nixpkgs pin `c59305b`).
- **Built:** 2026-10-26, on x86_64-linux. The host dictionary describes the Linux MCU, and its commands don't depend on the CPU, so an x86_64 build stands in for the CB1's aarch64 one.

## Regenerating

Regenerate whenever cb1-autopipette's Klipper pin or one of the Kconfigs changes:

1. Copy any changed Kconfig from cb1-autopipette's `config/` here.
2. Run `tests/dicts/regen.sh`. It builds each firmware with `build.nix` at cb1's pinned nixpkgs and prints the Klipper rev. Set `CB1_FLAKE` to use a local cb1 checkout.
3. Update the rev and date above.
4. Re-run `tests/run.sh` and re-check the batch-mode facts in `../README.md`.

Each dictionary's `version` field contains its build time, so a rebuild changes the files even when nothing else did.
