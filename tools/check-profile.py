#!/usr/bin/env python3
"""Check the custom profile in the materialized manifests is the one the overlay asks for.

The pin plus the overlay is the whole design, so this proves the profile still resolves to
the module list we expect rather than to a silently shorter one. Run it after
`tools/materialize.py`; it reads `.ecc/manifests/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MANIFESTS = REPO / ".ecc" / "manifests"
OVERLAY = REPO / "overlay" / "manifest-overlay.json"


def main() -> int:
    if not MANIFESTS.is_dir():
        sys.exit("no .ecc/manifests — run `python3 tools/materialize.py` first")

    modules = json.loads((MANIFESTS / "install-modules.json").read_text())["modules"]
    profiles = json.loads((MANIFESTS / "install-profiles.json").read_text())["profiles"]
    expected = json.loads(OVERLAY.read_text())["addProfiles"]["custom"]["modules"]

    got = profiles.get("custom", {}).get("modules")
    if got is None:
        sys.exit("the custom profile is missing from the materialized manifests")
    if got != expected:
        sys.exit(f"custom profile drifted:\n  overlay says {expected}\n  manifest says {got}")

    known = {m["id"] for m in modules}
    missing = [m for m in got if m not in known]
    if missing:
        sys.exit(f"custom profile names modules that do not exist: {missing}")

    print(f"custom profile resolves to {len(got)} modules, all present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
