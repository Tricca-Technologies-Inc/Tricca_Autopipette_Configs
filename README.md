# Tricca AutoPipette Klipper config

This is the Klipper config set for the Tricca AutoPipette. cb1-autopipette pins this repo (`printer-cfgs`) and seeds every root `*.cfg` onto each machine. Only files that belong on a machine go at the root, and anything test-only lives in `tests/`.

## Files

| File | Contents |
|---|---|
| `printer.cfg` | Includes, `[mcu CB1]` (host MCU), idle timeout, pause-in-place |
| `mainsail.cfg` | Mainsail's client macros |
| `tricca-autopipette.cfg` | Manta M8P V2.0: the gantry (X, Y, four Z), `pipette_stepper` and `pipette_servo`, and `[homing_override]` |
| `octopus-plates.cfg` | BTT Octopus V1.1 (**non-Pro**, STM32F446): six plate-drawer steppers `plate1`…`plate6`, 0…350 mm, NC home switches at the "in" end |
| `plate-macros.cfg` | Plate axes, the pipette on G-code axis P, homing, and the collision interlock |
| `moonraker.conf` | Moonraker |
| `tests/` | Offline Klipper tests (batch mode); see [tests/README.md](tests/README.md) |

### MCUs are machine-written

**No MCU serial ID or CAN UUID ever goes in this repo.** cb1-autopipette's `bootstrap.sh` detects each board and writes its section into the machine's own `printer.cfg`:

- `[mcu]` is the M8P over USB (`stm32h723xx`).
- `[mcu octopus]` is the Octopus over USB (`stm32f446xx`).

The EBB42 CAN toolboard is deferred, so the pipette stays on the M8P.

## Interlock

`plate-macros.cfg` keeps the pipette tip and the plate drawers from colliding. All checks use raw machine coordinates (`gcode_move.position`), so `G92` and G-code offsets can't fool them. Z0 is the tip fully raised, and a larger Z lowers it.

| Rule | When | Requirement |
|---|---|---|
| I1 | `G1`/`G0` with a plate letter | Z homed; raw Z ≤ `z_safe` now and at the target; the moving plates homed |
| I2 | `G1`/`G0` lowering the tip below `z_safe` | Every plate homed and within `park_tol` of one of its own **tip-safe positions** |
| I3 | `MANUAL_STEPPER STEPPER=plateN` | Only from the plate macros |
| I4 | `HOME_PLATE(S)` / `G28 U…C` | Z homed and raw Z ≤ `z_safe` |
| I5 | A stepper disabled (`M84`/`M18`, `SET_STEPPER_ENABLE`, Klipper's own motors-off), restart, E-stop | It becomes unhomed |
| I6 | `G1`/`G0` with `P` | Plunger homed and P bound |

I2 also covers `SET_GCODE_OFFSET … MOVE=1`, `RESTORE_GCODE_STATE … MOVE=1`, `RESUME` (which restores through it) and `STEPPER_BUZZ` on a Z stepper. `MANUAL_PROBE` and `Z_ENDSTOP_CALIBRATE` are refused outright. Every command Klipper registers is classified in `tests/command-inventory.txt`, and the tests fail on any command that isn't listed there.

### Tip-safe positions

`_PLATE_CFG`'s `variable_safe_stops` lists, for each plate, the positions (mm) where the tip may go below `z_safe`. The default is `[0, 350]` for every plate (fully in or fully out). To allow pipetting into a drawer at, say, 120 mm, add it to that plate's list:

```ini
variable_safe_stops: {'plate1': [0, 120, 350], 'plate2': [0, 350], ...}
```

- A plate missing from the list is never tip-safe.
- Klipper is the authority. tapd reads this list through Moonraker and refuses a drawer stop marked `pipetting` that isn't on it (within `park_tol`).
- tapd keeps its own copy of the stops in `config/locations/*.json`, and the two are kept in step by hand.

### Never

- Never send `G1.1`, `G0.1`, any `*_BASE` command, `M84.1`, `M18.1`, `_PLATE_INTERNAL=1`, or `SET_GCODE_VARIABLE` on `_PLATE_CFG`, `_PLATE_STATE`, `_PIPETTE_CFG`, `_PIPETTE_STATE` or `_GSTATE`. They are the renamed originals and the interlock's own state, so they bypass the checks.
- Never enable `[gcode_arcs]` or `[force_move] enable_force_move`.
- Never write `{-x}` in a template, because Jinja drops the minus sign. Write `{0 - x}`.
- Never add a config section that adds motion commands (probe, Z tilt, bed mesh) without a check and a test.

## G-code contract (with tapd)

| Command | Meaning | Stage |
|---|---|---|
| `G28` | Z, X, Y, park, plates 1–6, plunger | 1 |
| `G28 <X\|Y\|Z…>` | Named gantry axes (Z, X, Y order), then park the axes that are homed | 1 |
| `G28 <U\|V\|W\|A\|B\|C…>` | Named plates (requires Z homed and raised) | 1 |
| `G28 P` | Plunger | 1 |
| `HOME_PLATE PLATE=plateN`, `HOME_PLATES`, `HOME_PIPETTE` | Same as the `G28` forms | 1 |
| `PLATE_MOVE PLATE=plateN POS=<mm> [SPEED=<mm/s>]`, `PLATE_IN`, `PLATE_OUT`, `PLATES_IN` | Plate motion through the interlock. `POS` is a stop's mm value; Klipper knows no stop names | 1 |
| `QUERY_PLATES` | Text report for humans (homed, position, tip-safe) | 1 |
| `G1 … U…C…` / `G1 … P…` | Allowed; same interlock | 1 |
| `MANUAL_STEPPER STEPPER=pipette_stepper …` (no `SYNC=0`) | Today's tapd plunger commands | **1 only** |
| `G90` + `G1 P<abs>` | Plunger moves in stage 2 | 2 |
| `G90`, `G91`, `M84`, `SET_SERVO`, `SET_VELOCITY_LIMIT ACCEL=` | Existing tapd commands. `M84` also clears every homed flag | 1 / 2 |
| `STEPPER_BUZZ STEPPER=…` | Wiring check. A plate needs Z homed and the tip raised; a Z stepper needs every plate tip-safe | 1 |
| `PAUSE` / `RESUME` | `RESUME` is refused (the run stays paused) if returning the tip would hit a drawer | 1 |
| Error text `Move refused by interlock: <reason>` / `… refused: …` | Interlock refusals | 1 |
| Moonraker objects `gcode_macro _PLATE_CFG` (`axes`, `z_safe`, `park_tol`, **`safe_stops`**), `_PLATE_STATE`, `_PIPETTE_CFG`, `_PIPETTE_STATE`, `stepper_enable`, `gcode_move`, `configfile` | State tapd reads | 1 |

`variable_stage` in `_PIPETTE_CFG` selects the stage. Stage 2 also adds `position_min`/`position_max` to `[manual_stepper pipette_stepper]`, and the tests' lint checks that the two agree.

## Testing

```sh
tests/run.sh
```

This runs every offline case against this repo with the Klipper that cb1-autopipette pins. Hardware checks (homing switches, directions, latency) are the M-tests in the axis-expansion plan.
