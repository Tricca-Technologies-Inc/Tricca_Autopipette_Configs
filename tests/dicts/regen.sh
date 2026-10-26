#!/usr/bin/env bash
# Rebuild m8p.dict, octopus.dict and host.dict from the Kconfigs next to them,
# at the Klipper rev cb1-autopipette pins. Run after every Klipper pin bump
# (or Kconfig change), then re-run the tests and update README.md here.
#
# CB1_FLAKE as in ../run.sh.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cb1=${CB1_FLAKE:-github:Tricca-Technologies-Inc/cb1-autopipette}
nixpkgs=$(nix eval --raw --inputs-from "$cb1" nixpkgs#path)
for mcu in m8p octopus host; do
  out=$(nix-build --no-out-link "$here/build.nix" --arg nixpkgs "$nixpkgs" -A "$mcu")
  install -m644 "$out/klipper.dict" "$here/$mcu.dict"
done
echo "klipper rev: $(nix-instantiate --eval --raw "$here/build.nix" --arg nixpkgs "$nixpkgs" -A klipperRev)"
