"""Vendor the kit into a tool, or check a vendored copy (UI_STANDARD §14, D-UI1).

    py tools/vendor.py <tool>/ui/kit            copy kit/ there, write VERSION and HASHES.json
    py tools/vendor.py <tool>/ui/kit --check    exit 1 if any file differs from HASHES.json (edited by hand) or is missing

A tool's test calls check() so a hand edit of the vendored kit fails that tool's suite: changes go to gc-ui-kit and
are re-vendored. The kit folder in a tool holds exactly the files of kit/ plus VERSION and HASHES.json.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "kit"
SHIPPED = ["gc_tokens.css", "gc_tokens.json", "gc_ui.css", "gc_ui.js", "gc_server.py", "common_glossary.json"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def vendor(dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.iterdir():
        if old.name not in SHIPPED + ["VERSION", "HASHES.json"]:
            continue                       # never delete anything else that may sit there
    hashes = {}
    for name in SHIPPED:
        shutil.copy2(KIT / name, dest / name)
        hashes[name] = sha(dest / name)
    (dest / "VERSION").write_text(version() + "\n", encoding="utf-8")
    (dest / "HASHES.json").write_text(json.dumps({"kit": version(), "files": hashes}, indent=1) + "\n", encoding="utf-8")
    return hashes


def check(dest: Path) -> list[str]:
    """Problems with a vendored copy: [] when every shipped file matches HASHES.json."""
    dest = Path(dest)
    bad = []
    hp = dest / "HASHES.json"
    if not hp.exists():
        return [f"{dest}: no HASHES.json (not vendored with tools/vendor.py)"]
    h = json.loads(hp.read_text(encoding="utf-8"))
    for name, digest in h["files"].items():
        p = dest / name
        if not p.exists():
            bad.append(f"{name}: missing")
        elif sha(p) != digest:
            bad.append(f"{name}: differs from the vendored kit {h['kit']} (edit gc-ui-kit and re-vendor)")
    v = (dest / "VERSION").read_text(encoding="utf-8").strip() if (dest / "VERSION").exists() else None
    if v != h["kit"]:
        bad.append(f"VERSION {v} != HASHES.json kit {h['kit']}")
    return bad


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    dest = Path(argv[0])
    if "--check" in argv:
        bad = check(dest)
        for b in bad:
            print("FAIL", b)
        print("ok" if not bad else f"{len(bad)} problem(s)")
        return 1 if bad else 0
    h = vendor(dest)
    print(f"vendored kit {version()} into {dest}: {len(h)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
