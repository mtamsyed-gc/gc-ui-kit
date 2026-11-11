"""GC UI kit tests: tokens and contrast, JS lint, glossary schema, the server on a fake tool. Plain Python.

    py tests/test_kit.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit"))
sys.path.insert(0, str(ROOT / "tools"))
import build_tokens as BT  # noqa: E402
import gc_server as GS  # noqa: E402
import vendor as VD  # noqa: E402

FAILS = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        FAILS.append(msg)


# ---------------------------------------------------------------- 1. tokens
def test_tokens():
    tokens = json.loads((ROOT / "kit" / "gc_tokens.json").read_text(encoding="utf-8"))
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        bad = BT.check_pairs(tokens)
    check(not bad, f"every contrast pair passes in light and dark ({len(tokens['contrast_pairs'])} pairs)")
    check((ROOT / "kit" / "gc_tokens.css").read_text(encoding="utf-8") == BT.build(tokens), "gc_tokens.css is built from gc_tokens.json")
    css = (ROOT / "kit" / "gc_ui.css").read_text(encoding="utf-8")
    literal = [m.group(0) for m in re.finditer(r"#[0-9a-fA-F]{3,8}\b", css)]
    check(not literal, f"gc_ui.css has no literal colours (found {literal[:3]})")
    check("prefers-reduced-motion" in css and ":focus-visible" in css and ".skip" in css, "reduced motion, focus ring and skip link present")


# ---------------------------------------------------------------- 2. JS lint
def test_js():
    js = (ROOT / "kit" / "gc_ui.js").read_text(encoding="utf-8")
    bad = re.findall(r"(?<![\w.])(?:window\.)?(alert|confirm|prompt)\(", js)
    # the kit's own confirm()/prompt() are defined as functions and called bare: allow definitions and the kit's calls
    calls = [m for m in re.finditer(r"(?<![\w.])(alert)\(", js)]
    check(not calls, "no window.alert in gc_ui.js")
    check("window.confirm" not in js and "window.prompt" not in js, "no window.confirm / window.prompt")
    check("aria-live" in js and "aria-expanded" in js and "role:" in js, "ARIA live region, expanded state and roles present")
    r = subprocess.run(["node", "--check", str(ROOT / "kit" / "gc_ui.js")], capture_output=True, text=True) if shutil.which("node") else None
    check(r is None or r.returncode == 0, "node --check gc_ui.js" + ("" if r is None else (": " + r.stderr.strip()[:200])))
    # 1.2.1: VERSION, the page's KIT and the server's KIT_VERSION are one number (a tool test compares them)
    ver = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    srv = (ROOT / "kit" / "gc_server.py").read_text(encoding="utf-8")
    check(f'const KIT = "{ver}"' in js and f'KIT_VERSION = "{ver}"' in srv, f"VERSION {ver} = gc_ui.js KIT = gc_server.py KIT_VERSION")
    # 1.2.1: runButton waits for an async args dialog, sends its answers, and a cancelled dialog starts no run
    r = subprocess.run(["node", str(ROOT / "tests" / "js_runbutton.js")], capture_output=True, text=True) if shutil.which("node") else None
    check(r is None or r.returncode == 0, "runButton awaits its dialog" + ("" if r is None else (": " + (r.stdout + r.stderr).strip()[:300])))


# ---------------------------------------------------------------- 3. glossary
def test_glossary():
    g = json.loads((ROOT / "kit" / "common_glossary.json").read_text(encoding="utf-8"))
    terms = [e["term"].lower() for e in g]
    check(len(terms) == len(set(terms)), "glossary terms unique")
    bad = [e["term"] for e in g if not e.get("definition") or len(re.split(r"(?<=[.!?])\s+", e["definition"].strip())) > 3]
    check(not bad, f"definitions present and at most ~2-3 sentences ({bad[:3]})")
    cats = {e.get("category") for e in g}
    check(cats <= {"data", "method", "treaty", "check", "file", "general"}, f"categories in the schema ({cats})")
    known = set(terms) | {a.lower() for e in g for a in e.get("aliases", [])}
    dangling = [(e["term"], s) for e in g for s in e.get("see_also", []) if s.lower() not in known]
    check(not dangling, f"see_also entries resolve ({dangling[:3]})")


# ---------------------------------------------------------------- 4. server on a fake tool
def make_fake(tmp: Path):
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    client = tmp / "client"
    (client / "02_Inputs").mkdir(parents=True)
    (client / "01_Info").mkdir()
    (client / "out" / "csv").mkdir(parents=True)
    (client / "docs").mkdir()
    (client / "secret").mkdir()
    (client / "secret" / "x.csv").write_text("a,b\n1,2\n")
    (client / "out" / "csv" / "t.csv").write_text("code,severity,n\nA1,STOP,3\nB2,FLAG,1\nC3,OK,0\n", encoding="utf-8")
    (client / "docs" / "guide.md").write_text("# Guide\n\n## Mapping assist\nThe prompt text.\n\n## Other\nno\n", encoding="utf-8")
    wb = Workbook()
    ws = wb.active
    ws.title = "Settings"
    ws.append(["Setting", "Value", "Note", "Check"])
    ws.append(["payer", "ABC", "short name", "ok"])
    ws.append(["start", "2026-01-01", "date", "ok"])
    ws.append(["mode", "SIMPLE", "pick", "ok"])
    yellow = PatternFill("solid", fgColor="FFFFF2CC")
    red = PatternFill("solid", fgColor="FFC00000")
    blue = PatternFill("solid", fgColor="FFDDEBF7")
    for r in range(2, 5):
        ws.cell(row=r, column=2).fill = yellow
        ws.cell(row=r, column=3).fill = blue
        ws.cell(row=r, column=4).fill = red
    dv = DataValidation(type="list", formula1='"SIMPLE,FULL"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add("B4")
    ws2 = wb.create_sheet("Ref")
    ws2.append(["Code"])
    for i in range(5):
        ws2.append([f"R{i}"])
    wb.save(client / "02_Inputs" / "Book.xlsx")
    ui = tmp / "ui"
    (ui / "fake").mkdir(parents=True)
    shutil.copytree(ROOT / "kit", ui / "kit")
    script = ui / "fake" / "step.py"
    script.write_text("import sys,time,os\nprint('step', sys.argv[1:], 'ENV', os.environ.get('FAKE_CLIENT')); time.sleep(float(sys.argv[1]) if sys.argv[1:] else 0); print('DONE')\nsys.exit(int(sys.argv[2]) if len(sys.argv)>2 else 0)\n")
    (ui / "fake" / "plugin.py").write_text("def state(tool, runner):\n    return {'hello': tool.client.name}\n"
                                           "def api_echo(tool, q):\n    return {'echo': q.get('x')}\n"
                                           "def workbooks(tool):\n    return {'disc': {'path': '02_Inputs/Book.xlsx', 'title': 'Discovered'}, 'book': {'path': 'wrong', 'title': 'clash'}, 'bad id!': {'path': 'x'}}\n"
                                           "def sheet_help(tool, wid, sheet, columns):\n"
                                           "    if sheet != 'Settings': return {}\n"
                                           "    for c in columns:\n"
                                           "        if c['name'] == 'Value': c['description'] = 'the value'; c['required'] = True\n"
                                           "    return {'columns': columns, 'key_col': 1, 'value_col': 2, 'rows_help': {'payer': {'description': 'payer code', 'required': True, 'options': ['ABC', 'XYZ']}}, 'note': 'help note'}\n")
    (ui / "fake" / "glossary.json").write_text(json.dumps([{"term": "Burning cost", "definition": "Tool override.", "category": "method"},
                                                            {"term": "Payer tab", "definition": "The payer sheet.", "category": "file"}]))
    (ui / "fake" / "index.html").write_text("<!doctype html><title>fake</title>")
    manifest = {"name": "fake", "title": "Fake tool", "version": "0.1", "kit": "kit", "plugin": "plugin.py",
                "allowed_roots": ["02_Inputs", "01_Info", "out", "docs"], "state_dir": "ui_state", "lenai_dir": "07_LenAI",
                "watch_files": {"t": "out/csv/t.csv", "missing": "out/none.csv"},
                "editable_workbooks": {"book": {"path": "02_Inputs/Book.xlsx", "title": "Book", "readonly_sheets": ["Ref"]}},
                "actions": {"step": {"title": "Step", "command": ["{py}", str(script), "0.05"], "args": {"rc": {"choices": ["0", "1", "2"]}},
                                     "backup_before": ["02_Inputs/Book.xlsx"]},
                            "pos": {"title": "Pos", "command": ["{py}", str(script), "0"], "args": {"a": {"positional": True, "default": "-"}, "b": {"positional": True, "pattern": "[0-9]+"}}},
                            "path": {"title": "Path", "command": ["{py}", str(script), "0"], "args": {"f": {"positional": True, "rel_path": True}}, "env": {"FAKE_CLIENT": "{client}"}},
                            "slow": {"title": "Slow", "command": ["{py}", str(script), "30"]}},
                "lenai": {"map": {"title": "Mapping assist", "prompt_file": "docs/guide.md", "prompt_section": "Mapping assist",
                                  "attach": ["02_Inputs/Book.xlsx", "01_Info/none.csv"], "expected_return": "A digest.", "return_to": "02_Inputs"}},
                "glossary": ["kit/common_glossary.json", "glossary.json"], "doc_root": "{ui}/.."}
    (ui.parent / "KITDOC.md").write_text("# kit doc\n")
    (ui / "fake" / "manifest.json").write_text(json.dumps(manifest))
    return client, ui / "fake" / "manifest.json"


class Srv:
    def __init__(self, manifest, client):
        self.httpd = None
        ev = threading.Event()
        def ready(h):
            self.httpd = h; ev.set()
        self.t = threading.Thread(target=GS.serve, args=(manifest, client, 0, False), kwargs={"ready": ready}, daemon=True)
        self.t.start()
        ev.wait(5)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def get(self, path):
        with urllib.request.urlopen(self.url + path) as r:
            return r.status, json.loads(r.read()) if r.headers.get_content_type() == "application/json" else r.read()

    def post(self, path, body):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def geterr(self, path):
        try:
            return self.get(path)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def stop(self):
        self.httpd.shutdown()


def test_server():
    os.environ["GC_UI_TEST"] = "1"
    tmp = Path(tempfile.mkdtemp(prefix="gckit_"))
    client, manifest = make_fake(tmp)
    s = Srv(manifest, client)
    try:
        st, m = s.get("/api/manifest")
        check(st == 200 and m["name"] == "fake" and m["_server"]["kit"] == GS.KIT_VERSION, "manifest served with server info")
        st, b = s.get("/kit/gc_ui.css")
        check(st == 200 and b"gc-header" in b, "kit css served")
        st, j = s.geterr("/kit/../fake/manifest.json")
        check(st in (400, 404), "kit path traversal refused")
        st, j = s.get("/api/state")
        check(j["plugin"] == {"hello": "client"} and j["files"]["t"]["exists"] and not j["files"]["missing"]["exists"], "state: plugin + watched files")
        check(j["workbooks"]["book"]["exists"] and not j["workbooks"]["book"]["in_use"], "state: workbook present, not in use")
        # tables
        st, j = s.get("/api/table?path=out/csv/t.csv")
        check(j["columns"] == ["code", "severity", "n"] and j["n_rows"] == 3, "csv table")
        st, j = s.get("/api/table?path=out/csv/t.csv&q=flag")
        check(j["n_rows"] == 1 and j["rows"][0][0] == "B2", "csv table filter")
        st, j = s.geterr("/api/table?path=secret/x.csv")
        check(st == 404, "table outside allowed roots refused")
        st, j = s.geterr("/api/table?path=../client/secret/x.csv")
        check(st == 404, "table path traversal refused")
        st, j = s.get("/api/table?path=02_Inputs/Book.xlsx&sheet=Ref")
        check(j["sheet"] == "Ref" and j["n_rows"] == 5, "xlsx table by sheet")
        # docs
        st, b = s.get("/doc/docs/guide.md")
        check(st == 200 and b"Mapping assist" in b, "doc served")
        st, j = s.geterr("/doc/secret/x.csv")
        check(st == 404, "doc outside roots refused")
        # glossary merge
        st, j = s.get("/api/glossary")
        bc = [e for e in j["entries"] if e["term"] == "Burning cost"]
        check(len(bc) == 1 and bc[0]["definition"] == "Tool override." and any(e["term"] == "Payer tab" for e in j["entries"]), "glossary: tool entry overrides common, tool terms added")
        # workbook + sheet
        st, j = s.get("/api/workbook?id=book")
        check([x["name"] for x in j["sheets"]] == ["Settings", "Ref"] and j["sheets"][1]["readonly"], "workbook info with read-only sheet")
        st, j = s.get("/api/sheet?id=book&sheet=Settings")
        cols = j["columns"]
        check([c["kind"] for c in cols] == ["text", "input", "optional", "check"], f"column kinds from fills ({[c['kind'] for c in cols]})")
        check(cols[1].get("description") == "the value" and j.get("rows_help", {}).get("payer", {}).get("options") == ["ABC", "XYZ"] and j.get("note") == "help note", "plugin sheet_help merged (columns, rows_help, note)")
        st, e = s.get("/api/plugin/echo?x=7")
        check(st == 200 and e == {"echo": "7"}, "plugin GET route")
        st, e = s.geterr("/api/plugin/nope")
        check(st == 404, "unknown plugin route 404")
        st, cp = s.post("/api/copy", {"path": "out/csv/t.csv"})
        check(st == 200 and cp["path"].startswith("out/csv/t_") and (client / cp["path"]).exists(), f"copy endpoint ({cp})")
        st, cp = s.post("/api/copy", {"path": "secret/x.csv"})
        check(st == 404, "copy outside roots refused")
        check(cols[1]["options"] == ["SIMPLE", "FULL"], f"options from the data validation ({cols[1]['options']})")
        check(cols[3]["locked"] and not cols[1]["locked"], "check column locked")
        check(j["rows"][1]["v"][1] == "2026-01-01", f"date cell read as yyyy-mm-dd ({j['rows'][1]['v'][1]})")
        # save: locked column refused, formula refused, ok with backup, mtime conflict, lock file
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": j["mtime_ts"], "edits": [{"row": 2, "col": 4, "value": "x"}]})
        check(st == 400 and "not editable" in j["error"], "save into a check column refused")
        st, j0 = s.get("/api/sheet?id=book&sheet=Settings")
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": j0["mtime_ts"],
                                           "edits": [{"row": 2, "col": 2, "value": "XYZ"}, {"row": 4, "col": 2, "value": "FULL"}, {"row": 3, "col": 2, "value": "2026-02-01"}],
                                           "appends": [["note", "7", "", ""]]})
        check(st == 200 and j["changed"] == 4 and j.get("backup", "").startswith("02_Inputs/_ui_backup/"), f"save ok with backup ({j})")
        from openpyxl import load_workbook
        wb = load_workbook(client / "02_Inputs" / "Book.xlsx")
        ws = wb["Settings"]
        check(ws["B2"].value == "XYZ" and ws["B4"].value == "FULL" and ws["B3"].value.year == 2026 and ws["B3"].value.month == 2, "saved values typed (text, list, date)")
        check(ws["A5"].value == "note" and ws["B5"].value == 7 and ws["B5"].fill.fgColor.rgb in GS.INPUT_FILLS, "appended row typed and styled like the first data row")
        check(len(ws.data_validations.dataValidation) == 1, "data validation survives the save")
        wb.close()
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": j0["mtime_ts"], "edits": [{"row": 2, "col": 2, "value": "Q"}]})
        check(st == 409 and "changed on disk" in j["error"], "stale mtime refused (409)")
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": j0["mtime_ts"], "force": True, "edits": [{"row": 2, "col": 2, "value": "Q"}]})
        check(st == 200, "force save after a conflict")
        # 1.2.2: an operator picked or typed ('=', '<>') is stored as text, never as a formula, and stays editable
        st, j1 = s.get("/api/sheet?id=book&sheet=Settings")
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": j1["mtime_ts"], "edits": [{"row": 2, "col": 3, "value": "="}], "appends": [["op", "", "<>", ""]]})
        wb = load_workbook(client / "02_Inputs" / "Book.xlsx")
        ws = wb["Settings"]
        last = ws.max_row
        check(st == 200 and ws["C2"].value == "=" and ws["C2"].data_type == "s" and ws.cell(last, 3).value == "<>", f"'=' saved as text, not a formula ({ws['C2'].value!r}, {ws['C2'].data_type})")
        wb.close()
        st, j1 = s.get("/api/sheet?id=book&sheet=Settings")
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": j1["mtime_ts"], "edits": [{"row": 2, "col": 3, "value": "=<"}]})
        check(st == 200, f"a cell holding '=' as text is edited again ({j})")
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Ref", "mtime": None, "edits": [{"row": 2, "col": 1, "value": "Q"}]})
        check(st == 400 and "read-only" in j["error"], "read-only sheet refused")
        lock = client / "02_Inputs" / "~$Book.xlsx"
        lock.write_text("x")
        st, j = s.post("/api/sheet/save", {"id": "book", "sheet": "Settings", "mtime": None, "force": True, "edits": [{"row": 2, "col": 2, "value": "Z"}]})
        check(st == 409 and "open in Excel" in j["error"], "save refused while Excel holds the file")
        st, j = s.get("/api/state")
        check(j["workbooks"]["book"]["in_use"], "state shows the workbook in use")
        lock.unlink()
        baks = list((client / "02_Inputs" / "_ui_backup").glob("Book_*.xlsx"))
        check(len(baks) == 4, f"one backup per save: four kept ({len(baks)})")
        nb = len(baks)
        # open
        st, j = s.post("/api/open", {"path": "02_Inputs/Book.xlsx"})
        check(st == 200 and j["ok"], "open an allowed workbook")
        st, j = s.post("/api/open", {"path": "secret/x.csv"})
        check(st == 404, "open outside roots refused")
        (client / "out" / "run.cmd").write_text("x")
        st, j = s.post("/api/open", {"path": "out/run.cmd"})
        check(st == 403, "open a script refused")
        st, j = s.post("/api/open", {"path": "."})
        check(st == 200 and j["ok"], f"open the client folder itself ('.', 1.2.2) ({j})")
        st, j = s.post("/api/open", {"path": "./secret/x.csv"})
        check(st == 404, "a file under the client root but outside the roots still refused")
        # lenai
        st, j = s.post("/api/lenai", {"id": "map"})
        check(st == 200 and j["attached"] == ["Book.xlsx"] and j["missing"] == ["01_Info/none.csv"], f"lenai folder prepared ({j})")
        f = client / j["folder"]
        check((f / "PROMPT.md").read_text().startswith("## Mapping assist") and "Other" not in (f / "PROMPT.md").read_text(), "prompt = the named section only")
        check((f / "ATTACH" / "Book.xlsx").exists() and (f / "README.md").exists() and (f / "EXPECTED_RETURN.md").read_text() == "A digest.", "ATTACH, README, EXPECTED_RETURN written")
        # runs
        st, j = s.post("/api/run", {"action": "step", "args": {"rc": "0"}})
        check(st == 200 and j["run"]["action"] == "step", "run started")
        for _ in range(60):
            time.sleep(0.1)
            st, l = s.get("/api/log")
            if not l["running"]:
                break
        check(not l["running"] and l["run"]["rc"] == 0 and any("DONE" in x for x in l["lines"]), f"run finished rc 0 with log ({l['run']['rc']})")
        check(len(list((client / "02_Inputs" / "_ui_backup").glob("Book_*.xlsx"))) == nb + 1 and l["run"]["backups"], "backup_before kept a copy before the run")
        st, j = s.post("/api/run", {"action": "step", "args": {"rc": "9"}})
        check(st == 400 and "not one of" in j["error"], "bad choice argument refused")
        st, j = s.post("/api/run", {"action": "pos", "args": {"b": "x"}})
        check(st == 400 and "not a valid value" in j["error"], "positional pattern refused")
        rn = GS.Runner(GS.Tool(manifest, client))
        cmd = rn.command(rn.tool.action("pos"), {"b": "12"})
        check(cmd[-2:] == ["-", "12"], f"positional defaults and order ({cmd[-2:]})")
        st, j = s.post("/api/run", {"action": "nope"})
        check(st == 400, "unknown action refused")
        # 1.2.0: rel_path positional, env, plugin workbooks
        cmd = rn.command(rn.tool.action("path"), {"f": "02_Inputs/Book.xlsx"})
        check(cmd[-1] == str((client / "02_Inputs" / "Book.xlsx").resolve()), f"rel_path arg passed absolute ({cmd[-1]})")
        for bad in ("secret/x.csv", "../x", "02_Inputs/none.xlsx"):
            try:
                rn.command(rn.tool.action("path"), {"f": bad}); check(False, f"rel_path outside / missing refused ({bad})")
            except ValueError:
                check(True, f"rel_path outside / missing refused ({bad})")
        wbs = rn.tool.workbooks()
        check("disc" in wbs and wbs["book"]["title"] == "Book" and "bad id!" not in wbs, f"plugin workbooks merged, manifest wins, bad ids dropped ({sorted(wbs)})")
        st, j = s.get("/api/workbook?id=disc")
        check(st == 200 and j["exists"] and [x["name"] for x in j["sheets"]] == ["Settings", "Ref"], "discovered workbook served")
        st, j = s.get("/api/state")
        check("disc" in j["workbooks"], "discovered workbook in state")
        st, b = s.get("/doc/KITDOC.md")
        check(st == 200 and b"kit doc" in b, "doc served from doc_root")
        check(s.geterr("/doc/../KITDOC.md")[0] in (400, 404) and s.geterr("/doc/kit/gc_server.py")[0] == 404, "doc_root escape and non-doc refused")
        st, j = s.post("/api/run", {"action": "path", "args": {"f": "02_Inputs/Book.xlsx"}})
        for _ in range(60):
            time.sleep(0.1)
            st, l = s.get("/api/log")
            if not l["running"]:
                break
        check(any(f"ENV {client.resolve()}" in x for x in l["lines"]), "action env {client} substituted")
        st, j = s.post("/api/run", {"action": "step", "args": {"rc": "2"}})
        for _ in range(60):
            time.sleep(0.1)
            st, l = s.get("/api/log")
            if not l["running"]:
                break
        check(l["run"]["rc"] == 2, "exit code 2 recorded")
        st, j = s.post("/api/run", {"action": "slow"})
        st, j2 = s.post("/api/run", {"action": "step"})
        check(st == 409 and "already in progress" in j2["error"], "second run refused while one runs")
        st, j = s.post("/api/stop", {})
        for _ in range(50):
            time.sleep(0.1)
            st, l = s.get("/api/log")
            if not l["running"]:
                break
        check(not l["running"] and l["run"]["rc"] != 0, "stop terminates the run")
        st, j = s.get("/api/runs")
        check(len(j["runs"]) == 4, f"run history kept ({len(j['runs'])})")
        acts = (client / "ui_state" / "ui_actions.log").read_text()
        check("run step" in acts and "save book/Settings" in acts and "lenai map" in acts and "open 02_Inputs/Book.xlsx" in acts, "ui_actions.log audits run, save, lenai, open")
        # nothing deleted / written outside the allowed places
        check((client / "secret" / "x.csv").exists() and (client / "out" / "csv" / "t.csv").exists(), "client files untouched")
    finally:
        s.stop()
        shutil.rmtree(tmp, ignore_errors=True)


def test_vendor():
    tmp = Path(tempfile.mkdtemp(prefix="gcven_"))
    try:
        d = tmp / "ui" / "kit"
        VD.vendor(d)
        check(not VD.check(d), "vendored copy checks clean")
        (d / "gc_ui.css").write_text("/* edited */", encoding="utf-8")
        bad = VD.check(d)
        check(len(bad) == 1 and "gc_ui.css" in bad[0], "a hand edit is detected")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 1.2.2 per-row lists and lists Excel lets you type past
def test_row_options():
    from openpyxl import Workbook
    from openpyxl.worksheet.datavalidation import DataValidation
    import types
    wb = Workbook()
    ws = wb.active
    ws.title = "Cols"
    ref = wb.create_sheet("_lists")
    for i, v in enumerate(["P1", "P2"], 1):
        ref.cell(i, 1, v)
    for i, v in enumerate(["C1", "C2", "C3"], 1):
        ref.cell(i, 2, v)
    ws.append(["Raw", "Mapped", "Include"])
    for i in range(6):
        ws.append([f"r{i}", None, "Y"])
    a = DataValidation(type="list", formula1="=_lists!$A$1:$A$2", showErrorMessage=False)
    a.add("B2:B4")
    b = DataValidation(type="list", formula1="=_lists!$B$1:$B$3", showErrorMessage=False)
    b.add("B5:B7")
    c = DataValidation(type="list", formula1='"Y,N"', showErrorMessage=True)
    c.add("C2:C7")
    w = DataValidation(type="list", formula1='"Q"', showErrorMessage=True, errorStyle="warning")
    w.add("A2:A7")
    for v in (a, b, c, w):
        ws.add_data_validation(v)
    fake = types.SimpleNamespace(_dv_options=lambda wb_, ws_, f: GS.Tool._dv_options(None, wb_, ws_, f))
    m = GS.Tool.sheet_meta(fake, wb, ws, {})
    cols = {c_["name"]: c_ for c_ in m["columns"]}
    ro = cols["Mapped"].get("row_options")
    check(ro == [[2, 4, 0], [5, 7, 1]] and m["option_sets"] == [["P1", "P2"], ["C1", "C2", "C3"]], f"per-row lists: row_options and option_sets ({ro}, {m['option_sets']})")
    check(cols["Mapped"]["options"] == ["P1", "P2"], "column options = the first list (as before)")
    check(cols["Mapped"].get("free") and not cols["Include"].get("free") and cols["Raw"].get("free"), "free = Excel accepts a typed value (no alert, or a warning alert); a stop alert stays strict")
    check("row_options" not in cols["Include"], "one list for the whole column: no row_options")
    ws2 = wb.create_sheet("KV")
    ws2.append(["Setting", "Value"])
    for k in ("Version", "Collated input", "Valuation date"):
        ws2.append([k, None])
    one = DataValidation(type="list", formula1='"CSV,Parquet"', showErrorMessage=True)
    one.add("B3")
    ws2.add_data_validation(one)
    m2 = GS.Tool.sheet_meta(fake, wb, ws2, {})
    v = m2["columns"][1]
    check(v.get("row_options") == [[3, 3, 0]] and m2["option_sets"] == [["CSV", "Parquet"]], f"a list on one row only: offered on that row only ({v.get('row_options')})")
    js = (ROOT / "kit" / "gc_ui.js").read_text(encoding="utf-8")
    check("row_options" in js and "datalist" in js and "option_sets" in js, "the editor uses row_options and offers free lists as suggestions (datalist)")
    check("(c.row_options && r > 0) ? []" in js, "the editor gives rows outside every list no drop-down")


# ---------------------------------------------------------------- 1.2.2 one page per port
def test_port():
    import socket as so
    s = so.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    tmp = Path(tempfile.mkdtemp(prefix="gcport_"))
    client, manifest = make_fake(tmp)
    hs = []
    for _ in range(2):
        ev = threading.Event()
        threading.Thread(target=GS.serve, args=(manifest, client, port, False), kwargs={"ready": lambda h, e=ev: (hs.append(h), e.set())}, daemon=True).start()
        ev.wait(5)
    ports = [h.server_address[1] for h in hs]
    check(len(ports) == 2 and ports[0] == port and ports[1] != port, f"a second page on a busy port moves to another port ({ports})")
    check(not GS.ExclusiveServer.allow_reuse_address, "no SO_REUSEADDR (Windows would let two pages share a port)")
    for h in hs:
        h.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for t in (test_tokens, test_js, test_glossary, test_server, test_row_options, test_port, test_vendor):
        print(f"--- {t.__name__}")
        t()
    print(f"\n{len(FAILS)} failure(s)")
    sys.exit(1 if FAILS else 0)
