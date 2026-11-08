"""Build kit/gc_tokens.css from kit/gc_tokens.json and check every contrast pair (UI_STANDARD §8, §11).

    py tools/build_tokens.py            write the CSS, print the contrast table, exit 1 on a failing pair
    py tools/build_tokens.py --check    only check: the CSS must equal what the JSON builds, every pair must pass
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / "kit" / "gc_tokens.json"
CSS = ROOT / "kit" / "gc_tokens.css"

HEAD = ("/* GC UI kit — design tokens (UI_STANDARD §8). Generated from gc_tokens.json by tools/build_tokens.py; edit the\n"
        "   JSON, not this file. Light is the default; [data-theme=\"dark\"] is the second set (D-UI3). Every text /\n"
        "   background pair in gc_tokens.json contrast_pairs passes WCAG 2.2 AA (tests/test_kit.py). */\n")


def lum(hexcol: str) -> float:
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def build(tokens: dict) -> str:
    out = [HEAD]
    for sel, name in ((":root", "light"), ('[data-theme="dark"]', "dark")):
        out.append(sel + " {\n")
        line = "  "
        for k, t in tokens["sets"][name].items():
            piece = f"--{k}: {t['$value']};"
            if len(line) + len(piece) > 118:
                out.append(line.rstrip() + "\n")
                line = "  "
            line += piece + " "
        out.append(line.rstrip() + "\n")
        out.append(f"  color-scheme: {name};\n}}\n")
    return "".join(out)


def check_pairs(tokens: dict) -> list[str]:
    bad = []
    for name in ("light", "dark"):
        s = {k: t["$value"] for k, t in tokens["sets"][name].items()}
        for fg, bg, need in tokens["contrast_pairs"]:
            if fg not in s or bg not in s:
                bad.append(f"{name}: unknown token in pair {fg}/{bg}")
                continue
            c = contrast(s[fg], s[bg])
            flag = "" if c >= need else "  <-- FAIL"
            print(f"{name:5} {fg:>12} on {bg:<12} {c:5.2f} (need {need})" + flag)
            if c < need:
                bad.append(f"{name}: {fg} on {bg} = {c:.2f} < {need}")
    return bad


def main(argv):
    tokens = json.loads(JSON.read_text(encoding="utf-8"))
    css = build(tokens)
    bad = check_pairs(tokens)
    if "--check" in argv:
        if CSS.read_text(encoding="utf-8") != css:
            bad.append("gc_tokens.css is not what gc_tokens.json builds: run tools/build_tokens.py")
    else:
        CSS.write_text(css, encoding="utf-8")
        print(f"wrote {CSS}")
    for b in bad:
        print("FAIL", b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
