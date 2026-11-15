"""Kit 1.3.0 browser test: the new components and the editor fixes, clicked in a real Chrome (Playwright).

    py tests/test_kit_browser.py          (run by tests/test_kit.py; skips with exit 0 without Playwright / Chrome)

A fake tool page (built here, synthetic data only) on the kit server:
  - sortable list: drag a row, ▲ / ▼ buttons, Alt+arrow on a row, a filter the buttons step over; pinned rows never move,
    are never a drop target, have no buttons and cannot be removed
  - status dot: the label and the reasons in the tooltip and the screen-reader text; grey = Not assessed
  - thumbnail slot: an empty placeholder
  - editor, 0BO (1): a workbook that does not exist yet keeps Reload beside the banner; once the file is written, the
    poller reloads the open editor's body; a file changed on disk reloads it; with unsaved edits it says so instead
  - editor, 0BO (2): drag a header edge = a wider column, kept per workbook x sheet across a reload (localStorage);
    double-click = fit; storage that throws = the default widths, no page error; the Note column wraps
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "kit"))
FAILS = []


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


def browser_path():
    for p in (os.environ.get("CHROME"), shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"),
              r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        if p and Path(p).exists():
            return p
    return None


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>kit components</title>
<link rel="stylesheet" href="../kit/gc_tokens.css"><link rel="stylesheet" href="../kit/gc_ui.css"><script src="../kit/gc_ui.js"></script></head>
<body><main id="m"></main><script>
(async function () {
  const { el } = GC;
  const m = document.getElementById("m");
  window.changes = [];
  const items = [{ id: "A", label: "Cover", pinned: true }, { id: "B", label: "Bravo" }, { id: "C", label: "Charlie" },
                 { id: "D", label: "Delta" }, { id: "E", label: "Selections", pinned: true }];
  window.hideC = false;
  const list = GC.sortable({ items, label: "Pages", removable: true, visible: (it) => !(window.hideC && it.id === "C"),
    render: (it) => el("span", { class: "lbl" }, it.label), onChange: (xs, ev) => window.changes.push([xs.map((x) => x.id).join(""), ev]) });
  window.list = list;
  m.append(el("div", { id: "srt" }, list));
  m.append(el("div", { id: "dots" }, GC.statusDot("none", ["not computed until milestone 3"], "Cover"), GC.statusDot("flag", ["fill 60%", "TPA missing"], "Claims")));
  m.append(el("div", { id: "thumbs" }, GC.thumbSlot(null, "Cover")));
  const eds = {};
  for (const wid of ["book", "later"]) { const ed = GC.editor(wid, { limit: 50 }); eds[wid] = ed; m.append(el("div", { id: "ed-" + wid }, ed)); }
  window.eds = eds;
  eds.book.load(); eds.later.load();
  GC.poll(async () => { const st = await GC.api("/api/state"); for (const [w, ed] of Object.entries(eds)) ed.watch(st.workbooks[w]); return st; }, 500).start();
})();
</script></body></html>"""


def make_tool(tmp: Path):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
    client = tmp / "client"
    (client / "02_Inputs").mkdir(parents=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Settings"
    ws.append(["Setting", "Value", "Note", "Check"])
    ws.append(["payer", "ABC", "a long note that should wrap inside its cell when the column is narrower than the text", "ok"])
    ws.append(["start", "2026-01-01", "date", "ok"])
    for r in (2, 3):
        ws.cell(row=r, column=2).fill = PatternFill("solid", fgColor="FFFFF2CC")
    wb.save(client / "02_Inputs" / "Book.xlsx")
    ui = tmp / "ui"
    (ui / "fake").mkdir(parents=True)
    shutil.copytree(ROOT / "kit", ui / "kit", ignore=shutil.ignore_patterns("__pycache__"))
    (ui / "fake" / "index.html").write_text(PAGE, encoding="utf-8")
    m = {"name": "fake", "title": "Fake", "version": "0", "kit": "kit", "allowed_roots": ["02_Inputs"], "state_dir": "ui_state",
         "editable_workbooks": {"book": {"path": "02_Inputs/Book.xlsx", "title": "Book"},
                                "later": {"path": "02_Inputs/Later.xlsx", "title": "Later"}}, "actions": {}}
    (ui / "fake" / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return client, ui / "fake" / "manifest.json"


def write_later(client, value):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Main"
    ws.append(["Key", "Value"])
    ws.append(["k1", value])
    p = client / "02_Inputs" / "Later.xlsx"
    tmp = p.with_name("Later.tmp.xlsx")
    wb.save(tmp)
    os.replace(tmp, p)


def order(pg):
    return "".join(pg.eval_on_selector_all("#srt li.srow", "els => els.map(e => e.dataset.id)"))


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP playwright not installed (requirements-dev)")
        return 0
    chrome = browser_path()
    if not chrome:
        print("SKIP no Chrome / Chromium found")
        return 0
    import gc_server as GS
    import threading
    tmp = Path(tempfile.mkdtemp(prefix="gckitb_"))
    client, manifest = make_tool(tmp)
    ev, box = threading.Event(), {}
    threading.Thread(target=GS.serve, args=(manifest, client, 0, False), kwargs={"ready": lambda h: (box.update(h=h), ev.set())}, daemon=True).start()
    ev.wait(5)
    url = f"http://127.0.0.1:{box['h'].server_address[1]}/"
    errors = []
    try:
        with sync_playwright() as p:
            br = p.chromium.launch(executable_path=chrome, headless=True)
            ctx = br.new_context(viewport={"width": 1300, "height": 1000})
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in m.text else None)
            pg.goto(url)
            pg.wait_for_selector("#srt li.srow")
            # ---- sortable
            check(order(pg) == "ABCDE", "sortable: the items in their order")
            check(pg.locator('#srt li[data-id="A"] button').count() == 0 and pg.locator('#srt li[data-id="E"] button').count() == 0,
                  "pinned rows have no move or remove buttons")
            check(pg.locator('#srt li[data-id="A"]').get_attribute("draggable") is None, "a pinned row is not draggable")
            check(pg.locator('#srt li[data-id="B"] .up').is_disabled() and pg.locator('#srt li[data-id="D"] .down').is_disabled(),
                  "the first free row cannot move up past a pinned row, the last cannot move down")
            pg.locator('#srt li[data-id="B"] .down').click()
            check(order(pg) == "ACBDE", f"▼ moves a row down ({order(pg)})")
            check(pg.evaluate("document.activeElement && document.activeElement.closest('li') && document.activeElement.closest('li').dataset.id") == "B",
                  "focus stays on the moved row's button (keyboard use)")
            pg.keyboard.press("Enter")                        # the focused ▼ again, by keyboard
            check(order(pg) == "ACDBE", f"Enter on the focused ▼ moves it again ({order(pg)})")
            pg.locator('#srt li[data-id="B"]').focus()
            pg.keyboard.press("Alt+ArrowUp")
            check(order(pg) == "ACBDE", f"Alt+↑ on a row moves it up ({order(pg)})")
            pg.locator('#srt li[data-id="D"] .grip').drag_to(pg.locator('#srt li[data-id="C"]'), target_position={"x": 20, "y": 3})
            check(order(pg) == "ADCBE", f"drag a row before another ({order(pg)})")
            pg.locator('#srt li[data-id="D"] .grip').drag_to(pg.locator('#srt li[data-id="A"]'), target_position={"x": 20, "y": 3})
            check(order(pg) == "ADCBE", "a pinned row is never a drop target")
            pg.locator('#srt li[data-id="B"] .grip').drag_to(pg.locator('#srt li[data-id="E"]'), target_position={"x": 20, "y": 20})
            check(order(pg) == "ADCBE", "nothing is dropped after the pinned last row")
            pg.evaluate("window.hideC = true; window.list.refresh()")
            check(not pg.locator('#srt li[data-id="C"]').is_visible(), "a filtered row is hidden")
            pg.locator('#srt li[data-id="B"] .up').click()
            check(order(pg) == "ABDCE", f"▲ steps over a hidden row: B goes above D, the hidden C stays after D ({order(pg)})")
            pg.evaluate("window.hideC = false; window.list.refresh()")
            pg.locator('#srt li[data-id="C"] .del').click()
            check(order(pg) == "ABDE" and pg.evaluate("window.list.remove('A')") is False, "a free row can be removed, a pinned row cannot")
            ch = pg.evaluate("window.changes")
            check(len(ch) >= 5 and ch[-1][1].get("removed") is True, "onChange reports every move and the removal")
            # ---- status dot, thumbnail slot
            d0 = pg.locator("#dots .dot").nth(0)
            check("s-none" in d0.get_attribute("class") and d0.get_attribute("aria-label") == "Cover — Not assessed: not computed until milestone 3"
                  and "not computed" in d0.get_attribute("title"), "status dot: grey = Not assessed, the reason in the tooltip and the label")
            d1 = pg.locator("#dots .dot").nth(1)
            check("s-flag" in d1.get_attribute("class") and d1.get_attribute("title") == "Caveats\nfill 60%\nTPA missing", "status dot: Caveats with each reason on its own line")
            th = pg.locator("#thumbs .thumb")
            check(th.count() == 1 and "empty" in th.get_attribute("class") and th.locator("img").count() == 0 and "no preview" in th.inner_text(),
                  "thumbnail slot: an empty placeholder, no image")
            # ---- editor 0BO (1): missing, then written, then changed
            later = pg.locator("#ed-later")
            later.locator(".banner").wait_for()
            check("does not exist yet" in later.inner_text() and later.get_by_role("button", name="Reload").count() >= 1,
                  "a missing workbook keeps Reload beside the banner")
            write_later(client, "first")
            pg.wait_for_function("() => { const e = document.querySelector('#ed-later input[aria-label=\"Value row 2\"]'); return e && e.value === 'first'; }", timeout=10000)
            check(True, "the poller reloads the open editor once the file is written (no F5)")
            time.sleep(1.1)
            write_later(client, "second")
            pg.wait_for_function("() => { const e = document.querySelector('#ed-later input[aria-label=\"Value row 2\"]'); return e && e.value === 'second'; }", timeout=10000)
            check(True, "a file changed on disk reloads the editor's body")
            later.locator('input[aria-label="Key row 2"]').fill("edited")
            later.locator('input[aria-label="Key row 2"]').dispatch_event("change")
            time.sleep(1.1)
            write_later(client, "third")
            pg.wait_for_function("() => document.querySelector('#ed-later').innerText.includes('changed on disk')", timeout=10000)
            check(later.locator('input[aria-label="Key row 2"]').input_value() == "edited", "with unsaved edits the editor says the file changed and keeps the edits")
            later.locator(".banner").get_by_role("button", name="Reload").click()
            pg.wait_for_function("() => { const e = document.querySelector('#ed-later input[aria-label=\"Value row 2\"]'); return e && e.value === 'third'; }", timeout=10000)
            check(later.locator('input[aria-label="Key row 2"]').input_value() == "k1", "Reload shows the file and discards the edits")
            # ---- editor 0BO (2): widths
            book = pg.locator("#ed-book")
            book.locator("table.gc th", has_text="Value").wait_for()
            hv = book.locator("table.gc th", has_text="Value")
            w0 = hv.bounding_box()["width"]
            rs = hv.locator(".rs")
            b = rs.bounding_box()
            pg.mouse.move(b["x"] + 2, b["y"] + 5)
            pg.mouse.down()
            pg.mouse.move(b["x"] + 62, b["y"] + 5, steps=6)
            pg.mouse.move(b["x"] + 122, b["y"] + 5, steps=6)
            pg.mouse.up()
            w1 = hv.bounding_box()["width"]
            check(w1 > w0 + 80, f"drag a header edge widens the column ({w0:.0f} -> {w1:.0f} px)")
            stored = pg.evaluate("JSON.parse(localStorage.getItem('gc.colw.book.Settings'))")
            check(isinstance(stored, dict) and abs(stored.get("Value", 0) - w1) <= 3, f"the width is kept per workbook x sheet ({stored})")
            pg.reload()
            pg.locator("#ed-book table.gc th", has_text="Value").wait_for()
            w2 = pg.locator("#ed-book table.gc th", has_text="Value").bounding_box()["width"]
            check(abs(w2 - w1) <= 3, f"the width survives a reload ({w2:.0f} px)")
            note = pg.locator("#ed-book table.gc td.wrap").first
            check(note.count() == 1 and pg.evaluate("e => getComputedStyle(e).whiteSpace", note.element_handle()) == "normal", "the Note column wraps")
            check(pg.locator("#ed-book table.gc td.wrap textarea").count() >= 1, "an editable Note cell is a text area (several lines)")
            pg.locator("#ed-book table.gc th", has_text="Value").locator(".rs").dblclick()
            w3 = pg.locator("#ed-book table.gc th", has_text="Value").bounding_box()["width"]
            check(w3 < w2 - 40, f"double-click the edge fits the column to its content ({w2:.0f} -> {w3:.0f} px)")
            # ---- storage that throws: defaults, no page error
            ctx2 = br.new_context(viewport={"width": 1300, "height": 1000})
            ctx2.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocked by policy'); } });")
            pg2 = ctx2.new_page()
            errs2 = []
            pg2.on("pageerror", lambda e: errs2.append(str(e)))
            pg2.goto(url)
            pg2.locator("#ed-book table.gc th", has_text="Value").wait_for()
            hv2 = pg2.locator("#ed-book table.gc th", has_text="Value")
            wd = hv2.bounding_box()["width"]
            b = hv2.locator(".rs").bounding_box()
            pg2.mouse.move(b["x"] + 2, b["y"] + 5)
            pg2.mouse.down()
            pg2.mouse.move(b["x"] + 100, b["y"] + 5, steps=8)
            pg2.mouse.up()
            w_after = hv2.bounding_box()["width"]
            check(abs(wd - w0) <= 3 and w_after > wd + 60 and not errs2,
                  f"storage blocked: default widths, resizing still works, no page error ({w0:.0f} / {wd:.0f} -> {w_after:.0f}; {errs2[:1]})")
            ctx2.close()
            br.close()
    finally:
        box["h"].shutdown()
        shutil.rmtree(tmp, ignore_errors=True)
    check(not errors, f"no page or console error ({errors[:2]})")
    print(f"\n{len(FAILS)} failure(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
