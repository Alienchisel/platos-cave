#!/usr/bin/env python3
"""
Regenerate every committed artifact, and prove the committed copies were current.

    python tools/regen.py            # regenerate in place, report what moved
    python tools/regen.py --check    # exit 1 if anything was stale (for CI)

Why this exists: the repository commits things that are *derived* -- C headers,
the reference screens, the difficulty curves, the README's gameplay GIF -- and
nothing re-derived them automatically. Twice that produced artifacts describing a
game that no longer existed: the hero GIF outlived three changes to cave.py, and
the pacing tables outlived the per-region difficulty steps. Both were found by
eye, weeks late, and only by accident.

Generation is byte-reproducible, so "regenerate and see if git notices" is a
sound test. `--check` reports as stale only what *this run* changed, so
uncommitted work in progress is not mistaken for a finding.

Two generators need `image/plato.png`, the source photograph, which is not in the
repository. Those are skipped when it is absent -- loudly, and named in the
summary, because a green check that silently covered five of seven tools would be
worse than no check at all.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTO = ROOT / "image" / "plato.png"

# The committed PNGs and the GIF were rendered with Consolas. The tools now fall
# back to another monospace face elsewhere so they *run* on any machine -- but a
# different face moves pixels, and a pixel difference from the font is not
# staleness. Where the canonical font is absent, the tools that draw text are
# skipped rather than diffed.
sys.path.insert(0, str(ROOT / "tools"))
import cave                                          # noqa: E402
CANONICAL_FONT = Path(cave.CANONICAL_FONT).exists()

# Order matters: bake_assets writes bust.h, which bake_web reads.
FONT_GATE = "the canonical font (Consolas)"

# (tool, what must be present for its output to be comparable)
TOOLS = [
    ("bake_assets.py", PHOTO),
    ("bake_constants.py", None),          # pure text from cave.py, font-free
    ("bake_web.py", None),                # ditto, plus base64 out of bust.h
    ("mockups.py", PHOTO),
    ("stage_sheet.py", FONT_GATE),
    ("model_descent.py", FONT_GATE),
    ("readme_gif.py", FONT_GATE),
]

# Everything a generator is allowed to write. Anything dirty outside this set is
# hand-written and none of this script's business.
GENERATED = ["firmware/plato/assets", "web/index.html", "docs/images"]


def dirty():
    """Generated paths whose *content* differs from the committed version.

    `git diff`, not `git status`: on Windows the bakers rewrite files with CRLF
    while the index holds LF, so status reports every rewritten file as modified
    when nothing inside it changed. diff applies the .gitattributes
    normalisation and reports only real differences -- otherwise this guard
    would cry wolf on every run and be switched off within a week.
    """
    def run(cmd):
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace").stdout
    changed = run(["git", "diff", "--name-only", "--"] + GENERATED)
    # diff cannot see a generator that starts emitting a brand-new file.
    added = run(["git", "ls-files", "--others", "--exclude-standard", "--"] + GENERATED)
    return {q.strip() for q in (changed + added).splitlines() if q.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if a committed artifact was out of date")
    args = ap.parse_args()

    before = dirty()
    if before:
        print("already modified before this run, so not under test:")
        for p in sorted(before):
            print(f"    {p}")
        print()

    ran, skipped, failed = [], [], []
    for name, needs in TOOLS:
        why = None
        if needs is FONT_GATE and not CANONICAL_FONT:
            why = FONT_GATE
        elif isinstance(needs, Path) and not needs.exists():
            why = str(needs.relative_to(ROOT))
        if why:
            skipped.append((name, why))
            print(f"  skip  {name:<20} needs {why}, absent")
            continue
        r = subprocess.run([sys.executable, str(ROOT / "tools" / name)],
                           cwd=ROOT / "tools", capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
        if r.returncode != 0:
            failed.append(name)
            print(f"  FAIL  {name}")
            print("        " + (r.stderr.strip().splitlines() or ["(no output)"])[-1])
        else:
            ran.append(name)
            print(f"  ok    {name}")

    # verify_bake parses the generated C back out; there is no compiler here, so
    # it is the only thing that would catch structurally broken output. It
    # re-renders the bust from the photograph to compare, so it is gated on the
    # photograph too -- without that gate it failed the whole run on a clone
    # that simply does not have the file.
    if PHOTO.exists() and CANONICAL_FONT:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "verify_bake.py")],
                           cwd=ROOT / "tools", capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print(f"  {'ok   ' if r.returncode == 0 else 'FAIL '} verify_bake.py")
        if r.returncode != 0:
            failed.append("verify_bake.py")
            print("        " + (r.stdout.strip().splitlines() or ["(no output)"])[-1])
    else:
        why = str(PHOTO.relative_to(ROOT)) if not PHOTO.exists() else FONT_GATE
        skipped.append(("verify_bake.py", why))
        print(f"  skip  {'verify_bake.py':<20} needs {why}, absent")

    stale = sorted(dirty() - before)
    print()
    print(f"ran {len(ran)}, skipped {len(skipped)}, failed {len(failed)}")
    if skipped:
        print("NOT CHECKED (inputs absent): " + ", ".join(n for n, _ in skipped))
    if stale:
        print("\nSTALE -- the committed copies did not match what the tools produce:")
        for p in stale:
            print(f"    {p}")
        if args.check:
            print("\nRun `python tools/regen.py` and commit the result.")
    elif not failed:
        print("every artifact this run could check was already current")

    if failed:
        return 2
    return 1 if (stale and args.check) else 0


if __name__ == "__main__":
    sys.exit(main())
