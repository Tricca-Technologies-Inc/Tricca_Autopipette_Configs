# Offline Klipper tests

These tests run the pinned Klipper in **batch mode** (no boards attached) against this repo's config. Each test case runs in its own klippy process, and the script checks that case's errors or reported state. The interlock is safety-relevant, so it's tested here before it reaches a machine.

| File | Role |
|---|---|
| `run.sh` | Runs the tests with the Klipper and Python that cb1-autopipette pins (`nix shell --inputs-from`) |
| `run_offline_tests.py` | Builds a temporary, stubbed copy of the config, lints it, runs every case, and exits non-zero on any failure |
| `test-harness.cfg` | Test-only macros (`_T_HOME_PLATE`, `_T_HOME_ALL_PLATES`, `_T_STATE`, `_T_CMDS`). Included into the temporary copy only |
| `make_fixture.py` | Builds a "configs repo after CFG-1" (or after CFG-3 with `--stage 2`) from this repo plus the plan's `reference/klipper/`, so the tests can run before CFG-1 exists |
| `command-inventory.txt` | Every G-code command Klipper registers with this config, classified (checked, refused, bypass, no motion …). Case C-45 fails on any difference |
| `dicts/` | The firmware data dictionaries for the M8P, the Octopus and the host MCU, with their Kconfigs and a regeneration script (see `dicts/README.md`) |

**Nothing from here goes at the repo root**, because cb1-autopipette seeds every root `*.cfg` onto machines.

## Running

```sh
tests/run.sh                 # this repo, stage read from variable_stage
tests/run.sh --keep          # keep the work directory and klippy logs
tests/run.sh --config <dir>  # another config directory, e.g. a fixture
```

`run.sh` takes Klipper from cb1-autopipette's nixpkgs pin. By default that's cb1's GitHub `main`; set `CB1_FLAKE=<path or flake ref>` to use a local checkout. Any options are passed to `run_offline_tests.py`:

- `--klippy <command>` (default `klippy` on `PATH`) or `--klipper <checkout> --python <python>` selects klippy.
- `--dicts <dir>` (default `tests/dicts/`) selects the dictionaries.
- `--stage 1|2` overrides `variable_stage` in `_PIPETTE_CFG`.

The work directory goes under `$TMPDIR`.

Until CFG-1 is merged, this repo has no plate config and the run fails. Test a fixture instead:

```sh
REF=<Tricca_AutoPipette>/docs/plans/axis-expansion/reference/klipper
python3 tests/make_fixture.py --configs . --ref "$REF" --out /tmp/fx1
python3 tests/make_fixture.py --configs . --ref "$REF" --out /tmp/fx2 --stage 2
tests/run.sh --config /tmp/fx1 && tests/run.sh --config /tmp/fx2
```

## What the harness does

1. **Copies** the config's `*.cfg` into a temporary directory.
2. **Stubs the MCUs.**
   - Removes any `[mcu …]` sections. On a machine, bootstrap writes them with that board's serial ID, and no ID ever goes in this repo.
   - Adds `[mcu]` (M8P) and `[mcu octopus]` with `serial: /dev/null`, and keeps `[mcu CB1]`.
   - The dictionaries in `dicts/` provide each board's commands and pins.
   - There's no EBB42 (deferred, addendum D35). That also means there's no CAN MCU, which would crash batch mode in `canbus_bus_state` enumeration.
3. **Includes** `test-harness.cfg`.
4. **Lints** the configs. A lint failure fails the run.
   - `{-` or `-}` in a template: Jinja whitespace control silently drops the minus sign. Write `{0 - x}`.
   - `variable_stage` and the plunger soft limits on `[manual_stepper pipette_stepper]` in `tricca-autopipette.cfg` must agree (both stage 1 or both stage 2).
5. **Runs one process per case** and checks the result:
   - **Refusal cases:** the expected error must appear **and nothing may move**. The harness records the state just before and just after the refused command, and the axis map and positions must be identical.
   - **Any template crash** (an `Error evaluating …` that isn't a deliberate refusal) fails the case, even one expecting "no error".
   - **Any unexpected log line** fails the case. Only a short list of harmless lines and the expected refusal are allowed, so an unrecognised Klipper error can't pass silently. The harmless lines are state reports, "Pausing toolhead…", stepper enable notices, pause/resume actions and reactor timing dumps.
   - **Command inventory (C-45):** Klipper's full registered-command list must equal `command-inventory.txt`. When a config change, a Mainsail update or a Klipper bump adds a command, classify it there. If the new command can move Z, a plate or the plunger, also add an interlock check and a C-test.

## Batch-mode limits (verified at 7bc4d09)

Re-check these, and regenerate `dicts/`, whenever the Klipper pin changes.

| Limit | Consequence | Covered on hardware by |
|---|---|---|
| Homing moves never trigger early: each runs to its `MOVE` target, and the position is set to that target. Homing can't fail | G28 sequencing is tested. Switch behaviour is not: release checks, homing direction, trigger point. A failed `G28`'s motors-off is emulated with `M84.1`, which runs the same Klipper code (C-39) | M-02, M-03, M-04, M-14, M-23 |
| `delayed_gcode` doesn't fire before the input ends | Startup binding is tested by calling its body (`_PIPETTE_BIND`, case C-14b) | M-13 |
| Commands after an error still run | Every refusal case can check that the state didn't change | — |
| No real time or latency | Template cost per `G1` isn't measured | M-15 |
| No skipped steps or stalls | Commanded-state limits (WP2 §4) can't be exercised | Known limit |

## Cases

C-ids match WP2 §5.
- **Both stages:** C-01…C-12, C-14b, C-15, C-19, C-19c, C-21…C-28c, C-30, C-30b, C-31, C-33…C-35, C-38, C-38b, C-40…C-43, C-45.
- **Stage 1 only:** C-13, C-16, C-18, C-19b, C-20, C-32, C-32b, C-39…C-39c.
- **Stage 2 only:** C-13s, C-17…C-17c, C-19s, C-36s, C-37s.

The EBB-free fixture (configs `d7c45ce` + Rev L reference) passed 55/55 at stage 1 and 52/52 at stage 2 on 2026-10-26.
