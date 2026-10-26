#!/usr/bin/env bash
# Run the offline Klipper tests with the Klipper that cb1-autopipette pins.
#
#   tests/run.sh [run_offline_tests.py options]
#
# CB1_FLAKE selects the cb1-autopipette flake whose nixpkgs pin supplies
# klippy (default: its GitHub main; a local checkout works too, e.g.
# CB1_FLAKE=~/Documents/cb1-autopipette).
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cb1=${CB1_FLAKE:-github:Tricca-Technologies-Inc/cb1-autopipette}
exec nix shell --inputs-from "$cb1" nixpkgs#klipper nixpkgs#python3 \
  --command python3 "$here/run_offline_tests.py" "$@"
