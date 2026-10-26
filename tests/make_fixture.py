#!/usr/bin/env python3
"""Build a "configs repo after CFG-1 (or CFG-3)" from a Tricca_Autopipette_Configs
checkout plus the axis-expansion plan's reference/klipper/ files, so the offline
tests can run before CFG-1 exists. Applies reference/klipper/printer.cfg.md and
(for --stage 2) stage2.patch.md mechanically, with the EBB42 deferred
(addendum D35): the pipette sections stay in tricca-autopipette.cfg, and the
stage-2 plunger limits go there too.

Usage:
  make_fixture.py --configs <Tricca_Autopipette_Configs checkout>
                  --ref <Tricca_AutoPipette>/docs/plans/axis-expansion/reference/klipper
                  --out <dir> [--stage 1|2]

Once CFG-1 is merged, run run_offline_tests.py against the real repo instead.
"""
import argparse, os, re, shutil

SECTION = r"^\[{name}\]\n(?:(?!\[).*\n?)*"


def replace_in_section(text, name, pattern, repl):
    m = re.search(SECTION.format(name=re.escape(name)), text, flags=re.M)
    if not m:
        raise SystemExit(f"[{name}] section not found")
    body, n = re.subn(pattern, repl, m.group(0), count=1, flags=re.M)
    if n != 1:
        raise SystemExit(f"[{name}]: {pattern!r} not found")
    return text[:m.start()] + body + text[m.end():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", required=True)
    ap.add_argument("--ref", required=True, help="the plan's reference/klipper directory")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage", type=int, default=1, choices=[1, 2])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    for f in ("printer.cfg", "mainsail.cfg", "tricca-autopipette.cfg"):
        shutil.copy(os.path.join(a.configs, f), a.out)
    for f in ("octopus-plates.cfg", "plate-macros.cfg"):
        shutil.copy(os.path.join(a.ref, f), a.out)

    # printer.cfg: add the two includes after tricca-autopipette.cfg (no EBB)
    p = os.path.join(a.out, "printer.cfg")
    t = open(p).read()
    anchor = "[include tricca-autopipette.cfg]\n"
    if anchor not in t:
        raise SystemExit("printer.cfg: include anchor not found")
    t = t.replace(anchor, anchor + "[include octopus-plates.cfg]\n[include plate-macros.cfg]\n", 1)
    open(p, "w").write(t)

    # tricca-autopipette.cfg: pipette sections stay; homing_override replaced
    # by the reference section
    p = os.path.join(a.out, "tricca-autopipette.cfg")
    t = open(p).read()
    ho = open(os.path.join(a.ref, "homing_override.cfg.txt")).read()
    ho = ho[ho.index("\n[homing_override]\naxes") + 1:]
    t, n = re.subn(SECTION.format(name="homing_override"), lambda m: ho.rstrip("\n") + "\n\n",
                   t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit("tricca-autopipette.cfg: [homing_override] not found")
    if a.stage == 2:
        t = replace_in_section(t, "manual_stepper pipette_stepper", r"^(rotation_distance: .*\n)",
                               r"\1position_min: -60\nposition_max: 0\n")
    open(p, "w").write(t)

    if a.stage == 2:
        p = os.path.join(a.out, "plate-macros.cfg")
        t = open(p).read()
        t, n = re.subn(r"^variable_stage: 1$", "variable_stage: 2", t, flags=re.M)
        if n != 1:
            raise SystemExit("plate-macros.cfg: variable_stage not found")
        open(p, "w").write(t)
    print(f"fixture (stage {a.stage}) written to {a.out}")


if __name__ == "__main__":
    main()
