"""wow-ui-testing, our shared test library (wowproof, wowmock's client API snapshot): scripts/fetch-wut.sh puts the
commit .wut-version pins in the gitignored .wut/ (a no-op once there), or WUT_DIR names a local checkout instead.
PolyForm Noncommercial: used by tools/ only, never committed or shipped here."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FETCH = os.path.join(ROOT, "scripts", "fetch-wut.sh")


def library(needs):
    """The library's folder, fetched first if missing, or None when it can't be had or lacks `needs` (a file in it)."""
    run = subprocess.run(["bash", FETCH, ROOT], stdout=subprocess.PIPE, text=True)
    lines = run.stdout.strip().splitlines()
    lib = lines[-1] if run.returncode == 0 and lines else None
    return lib if lib and os.path.exists(os.path.join(lib, needs)) else None
