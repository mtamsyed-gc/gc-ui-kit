# gc-ui-kit changelog

Older entries (1.0.x - 1.2.2) are the "Manifest schema notes" in README.md. Each tool re-vendors on its own release
cycle (`py tools/vendor.py <tool>/ui/kit`, then set the manifest's `kit_build` to the new number).

## 1.3.0 (2026-11-15, Merit v10.5.0 / report builder milestone 2)

Minor bump: a new server route and a new plugin hook (no change to an existing manifest key; a tool that does not use
the new pieces behaves exactly as on 1.2.2).

- **Plugin write route** `POST /api/plugin/<name>`: a plugin declares `WRITE_ROUTES = {name: "relative path"}` and
  defines `post_<name>(tool, body, out_path) -> dict`. The plugin validates and writes the whole new file at `out_path`
  (a temporary file beside the target); the kit applies the rules of every write (UI_STANDARD §2.4): inside the allowed
  roots; refused (409) while Excel holds the file; refused (409) when the file changed on disk since the page read it
  (`mtime` in the body; `force` overrides), including "the page saw no file and one exists now"; a timestamped backup in
  `_ui_backup` (last 10 kept); the new file swapped in by one rename; audited in `ui_actions.log`. A refusal
  (`{"problems": [[code, message], ...]}`, `Refused`, or a `ValueError`) = 422 with every problem and nothing written.
  A function that is not declared in WRITE_ROUTES is never reached by POST. `api()` now gives the reply to the page as
  `error.data` (the problems).
- **`GC.sortable(opts)`**: an ordered list; drag a row (HTML5 drag and drop), or its ▲ / ▼ buttons (Tab to them; Enter /
  Space), or Alt+↑ / Alt+↓ on a focused row. Pinned rows (`item.pinned`) have no buttons, are not draggable, are never a
  drop target and cannot be removed: a move re-orders the free rows among the free positions only, so every pinned row
  keeps its index. `visible(item)` filters rows (▲ / ▼ step over hidden rows), `removable` adds ✕, `onChange(items, ev)`.
- **`GC.statusDot(status, reasons, label)`**: the fitness-of-data dot with the UI_STANDARD §6 colours: ok = Usable,
  flag = Caveats, stop = No data, none = Not assessed (grey); the reasons are the tooltip (one per line) and the
  screen-reader label. `GC.DOT` holds the words.
- **`GC.thumbSlot(src, alt)`**: a 16:9 thumbnail slot; without `src` an empty dashed placeholder ("no preview").
- **Editor, Merit 0BO (1)**: a workbook that does not exist yet (or a read error) keeps the toolbar and a Reload button
  beside the banner (before: the whole editor was replaced by the banner, only F5 recovered). New `editor.watch(ws)`:
  the page's poller passes the workbook's `{exists, mtime}` from `/api/state`; an editor that has been read reloads its
  body by itself when the file appears, disappears or its modified time changes; with unsaved edits it keeps them and
  shows "changed on disk - Reload" instead.
- **Editor, Merit 0BO (2)**: drag a header's right edge to resize the column; double-click the edge = fit the column to
  its content; widths kept per workbook x sheet in localStorage (`gc.colw.<workbook>.<sheet>`; reads and writes guarded,
  invalid values ignored; storage blocked or empty = the default widths, resizing still works for the page's life). A
  column named Note / Notes wraps; its editable cells are text areas.
- Tests: `tests/test_kit.py` (write route: new file, refusal with every problem, ValueError, conflict, "no file seen",
  backup, force, Excel lock, outside the roots, undeclared route, a route that writes nothing, the audit log) and the
  new `tests/test_kit_browser.py` (Playwright + Chrome, skips without): the sortable list by drag, buttons, keyboard and
  filter with pinned rows held; the dot; the slot; the editor's reload cases; widths by drag, across a reload, fit,
  storage blocked, the Note column.

- Run and Stop buttons a page re-renders away drop their listener (a page that redraws a card on every poll no longer accumulates them).
- Housekeeping: the committed `__pycache__` files are untracked (`.gitignore`).

### What the other tools gain at their next re-vendor (not re-vendored in this release)

- **Treaty workbench / TSM** (vendors 1.2.0): the editor fixes - Reload beside a missing-file banner, resizable and
  remembered column widths, the wrapping Note column - with no page change; `editor.watch()` once its page passes the
  workbook state from its poller (a one-line change); the 1.2.1 / 1.2.2 fixes it does not have yet (runButton awaits its
  dialog; per-row lists; one page per port). Checked here: its `tests/test_ui.py` passes on a copy re-vendored to 1.3.0
  with `kit_build` set to 1.3.0 (the one expected change).
- **XoL pricing tool** (vendors 1.1.1): the same editor fixes and everything since 1.1.1 (see README); not checked
  here (the xolpricing repository was not attached to this session).
