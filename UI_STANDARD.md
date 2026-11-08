# GC Tools UI Standard — UI-0.3

Status: agreed baseline, 2026-11-08 23:53. UI-0.2 recorded D-UI1 (kit home) and D-UI2 (launchers); UI-0.3 records
D-UI3 to D-UI6 (dark theme, LenAI folders, Power BI tile, in-page workbook editing) and the §2.4 write rule they need.
First implementation: Merit (ete-dashboard `side_tools/merit/ui`), kit 1.0.0 in `mtamsyed-gc/gc-ui-kit`.
Applies to: every browser front end of the owner's GC tools — XoL pricing tool (first adopter, kit 0.9.0), Merit
(next), Treaty Structure Metrics (TSM), pricing / tender workbench.
Reference implementation: `mtamsyed-gc/xolpricing` → `ui/kit/gc_ui.css`, `ui/kit/gc_ui.js`, `tools/ui/serve.py`,
`ui/xol/manifest.json`. Where this standard and the XoL page differ, this standard wins and XoL is retrofitted.

Keywords: **MUST** = required for conformance; **SHOULD** = default, deviation recorded in the tool's DESIGN.md;
**MAY** = optional.

---

## 0. Basis (the recognised standards this is built from)

| Layer | Source | How it is used here |
|---|---|---|
| Usability principles | ISO 9241-110:2020 (interaction principles), ISO 9241-11:2018 (usability) | §1: the seven principles, each turned into testable rules |
| Review heuristics | Nielsen's 10 usability heuristics (de facto) | §15: release review checklist |
| Accessibility | WCAG 2.2 level AA = ISO/IEC 40500:2025 | §11: the success criteria that matter for these pages |
| Visual language | Microsoft Fluent 2 (fits GC's Office estate) | Spacing grid, type ramp, focus and control sizing; GC navy / teal colours on top |
| Process patterns | GOV.UK Design System (task list, step-by-step, error summary, check answers) | §4, §7: stage list and input validation |
| Theming | Design tokens (W3C Design Tokens Community Group format) | §8: one tokens file shared by every tool |
| Documentation | Diátaxis (tutorial / how-to / reference / explanation); ISO/IEC/IEEE 26514 (user documentation) | §10: guide, glossary, index, help text |

---

## 1. Principles (ISO 9241-110) → rules

| # | Principle | Rule in these tools |
|---|---|---|
| P1 | Suitable for the task | One page holds the whole process: steps, launchers, workbooks, checks, LenAI prompts, docs. The user never needs File Explorer or a terminal for normal use. |
| P2 | Self-descriptive | Every stage card says what it does, what it needs, what it writes and what comes next. Every input has help (§7). |
| P3 | Conforms to expectations | Same layout, words, colours and status vocabulary in every tool (§3, §6, §9). Section numbers match the folder prefixes on disk. |
| P4 | Learnable | Guide with real screenshots, glossary, index and search reachable from every screen (§10). |
| P5 | Controllable | User chooses from / to stage, can stop a run, can re-run a stage; nothing runs without a click. |
| P6 | Error-tolerant | STOP checks block the next stage at the right point; destructive or long actions confirm first; the server never deletes files. |
| P7 | User engagement | Clear progress (live log, stage chips, elapsed time), plain-English messages, no clutter: admin and synthetic-test material hidden unless enabled. |

---

## 2. Architecture and launcher (MUST)

Decision taken from XoL 0.8.0+, which works on the GC laptop.

1. **Launcher**: one double-click file starts a local server (`serve.py`, Python **standard library only**) on
   `127.0.0.1` and opens the default browser. File type: `.cmd` in the pack (the GC laptop blocks downloaded `.bat`
   files; the owner sets up the launcher himself where needed). The launcher window stays open; closing it stops the
   server.
2. **Ports** (fixed, overridable by an argument): XoL 8765, Merit 8766, TSM 8767, workbench 8768. If the port is busy
   the launcher says so and offers the next free port.
3. **The page talks only to its own server** through a small JSON API (`/api/state`, `/api/run`, `/api/stop`,
   `/api/open`, `/api/log`, `/api/table`, plus tool-specific endpoints). Each tool declares its stages, files and
   prompts in a **manifest.json**; the page is generic, the manifest is specific.
4. **Server rules**: binds 127.0.0.1 only; reads and opens files only under the manifest's `allowed_roots`; opens only
   workbook / CSV / text / PDF / PBIX types (via `os.startfile`); **never deletes**; one pipeline run at a time; every
   open, copy, run and save appended to an `ui_actions.log` in the output folder; run state kept in `ui_run.json` so a
   reopened page shows the last run.
   **Writes (D-UI6, owner 2026-11-08)**: the server writes only (a) the workbooks the manifest lists as `editable`, only
   when the user presses Save in the page, after writing a timestamped backup to `<workbook folder>/_ui_backup/`
   (keep the last 10), and refusing with a clear message when Excel has the file open (lock file `~$name.xlsx` present
   or the open fails with a sharing violation); (b) LenAI assist folders (D-UI4, §5); (c) its own `ui_run.json`,
   `ui_actions.log`. Nothing else. Client data folders (raw files, outputs) are read-only to the server.
5. **No network**: no CDN, web fonts, analytics or external links in the page; all assets ship in the pack. The page
   works offline.
6. **Fallback (SHOULD)**: if `index.html` is opened directly (file://, no server), the page shows a banner "Server not
   running — start `<launcher>`" and still offers read-only content: guide, glossary, index, LenAI prompts with Copy,
   and each command with Copy.
7. **Existing launchers are called, never re-implemented (D-UI2, owner 2026-11-08)**: a run button invokes the tool's
   existing numbered `.cmd` launcher (Merit: `00_Start_Here\*.cmd`, `steps\*.cmd`) — one source of run logic, already
   laptop-tested, and the same launcher the user can double-click if the page is unavailable.
   - The page always passes the launchers' non-interactive arguments (`nopause`, `chained`, `diag` …); a server-run
     launcher must never wait for keyboard input.
   - Any decision a launcher would ask for (run menu, diagnostics YES, 03b review gate) is asked in an in-page confirm
     dialog and passed as an argument. A launcher without a non-interactive form for a decision gets one added in the
     tool (a tool change, versioned and laptop-tested) before the page exposes it.
   - Status is read from the files the run writes (checks CSVs, run manifest, logs), never parsed from console text.
   - Read-only state (file presence, workbook mtimes, table previews) is read by the server directly, without a
     launcher.
8. **Excel round trip**: a workbook tile offers *Open in Excel*; the server polls modification times; when a file
   changes after the last run, the dependent stages turn **STALE** and the page prompts a re-run (no manual refresh).

---

## 3. Page shell and information architecture (MUST)

```
┌ Header: tool name · version · client / run folder · overall status chip · Search (Ctrl+K) · Help ┐
├ Index (left, sticky)     ┤ Main                                                                   │
│ 0  Overview / checklist  │  section content (cards)                                               │
│ 1  Inputs                │                                                                        │
│ 2  Stages 01…nn          │                                                                        │
│ 3  Checks                │                                                                        │
│ 4  Results & deliverables│                                                                        │
│ 5  LenAI assists         │                                                                        │
│ 6  Help: guide, glossary,│                                                                        │
│    index, release notes  │                                                                        │
│ 7  Admin (hidden)        │                                                                        │
├ Status bar: server state · last run (started, finished, duration, exit) · kit version            ┘
```

- Every section has a stable anchor (`#stage-03`, `#glossary-burning-cost`) so guides and LenAI prompts can deep-link.
- Index entries carry the section's status chip (§6), so the index doubles as a progress view (GOV.UK task list).
- Section order = run order = folder prefix order. For Merit: `00_Start_Here` → Overview; `01_Info_Supplied` +
  `02_Inputs` → Inputs; `03_Workflows` 01…05 (incl. 03b) → Stages; `05_Checks` → Checks; `04_Outputs` +
  `06_Deliverables` → Results; `lenai/` and `docs/LENAI_*` → LenAI assists; `Admin_Upload` → Admin.
- **Admin** section (synthetic tests, admin upload, build tools, diagnostics) is hidden behind a header toggle and
  never shown by default.
- Minimum supported width 1280 px (laptop); SHOULD remain usable at 200% zoom (reflow, no horizontal page scroll).

---

## 4. Stage card anatomy (MUST)

Each pipeline step is one card with these parts in this order:

1. **Number and title** — `03  Claims intake` (number = folder prefix).
2. **Status chip** (§6) and last-run time.
3. **Purpose** — one sentence.
4. **Needs** — prerequisite stages and input files/workbooks, each with a present / missing / changed marker.
5. **Actions** — primary button (verb: *Run 03*, *Run 03 to 05*), secondary (*Open log*, *Open output folder*,
   *Copy command*). Long runs show an expected duration ("about 5–8 min on the owner's laptop").
6. **Checks summary** — counts of STOP / FLAG / INFO, expandable to the rows; STOP rows first.
7. **Outputs** — files written, with Open; key result tables inline (first rows, sortable).
8. **Next step** — one line pointing to the next card or a decision ("Copy the indicated factors into …").

Cards collapse; a card with STOP or FLAG opens automatically. The overall page shows a single **error summary**
banner at the top listing every STOP with a link to its card (GOV.UK error summary pattern).

---

## 5. Standard components (MUST use the kit, not hand-rolled variants)

| Component | Behaviour |
|---|---|
| Launcher button | Runs a manifest-declared command through the server; disabled while another run is active; shows a spinner and elapsed time. |
| Command card | Shows the exact command (mono, read-only) with **Copy**; **Run** when the server is up. Used for every `.cmd` / `py` step so no one types a command. |
| Workbook tile | Name, path, last saved, *Open in Excel*, *Copy template* when missing, STALE marker when changed since the last run. |
| Workbook editor (D-UI6) | In-page editing of a manifest-declared workbook: sheets as tabs; each cell typed per the input reference (§7); dirty marker; **Save** (server writes with backup, §2.4), **Discard**; a banner "Open in Excel: close it before saving" when the lock file exists; after Save the dependent stages go STALE. The page re-reads the file when its mtime changes outside the page and asks before overwriting the user's unsaved edits. |
| Power BI tile (D-UI5) | Shows the .pbix / .pbip path, its last modified time and the last data refresh time read from the run manifest; *Open in Power BI Desktop*; nothing else (dashboard figures are not repeated on the page). |
| File list | Required files per input folder with ✓ / ✗, size, modified time. |
| LenAI prompt card | Title; *when to use*; *what to attach* (files, columns); prompt text (mono, read-only, versioned e.g. `EA-1.0`); **Copy prompt**; **Prepare LenAI folder** (D-UI4, owner 2026-11-08): the server writes `<client>/07_LenAI/<yyyymmdd_HHMM>_<assist>/` holding `PROMPT.md` (the prompt), `ATTACH/` (copies of the files to attach, or the extract the assist needs), `README.md` (what to drag into LenAI, in which order, and where to save the return) and `EXPECTED_RETURN.md` (the Run Digest format); the page then offers *Open folder*. Prompt text is loaded from the same file the LenAI docs use (single source). |
| Status chip / pill | §6 vocabulary; icon + text + colour. |
| Banner | info / ok / flag / stop; one per message; dismissible except STOP. |
| Table | Sticky header, sortable, number columns right-aligned, row count shown, first N rows with *Open full CSV*. |
| Log viewer | Tail of the run log, auto-scroll toggle, *Copy log*, *Open log file*. |
| Confirm dialog | In-page modal (never browser `alert` / `confirm`), states the consequence, default focus on *Cancel*. |
| Toast | Short confirmations ("Copied", "Results copy saved"), auto-dismiss 4 s, announced to screen readers. |
| Help tip | "?" icon next to any input or term; opens the glossary entry or input reference in a side panel. |

---

## 6. Status vocabulary (MUST — identical in every tool)

| State | Meaning | Colour token | Icon |
|---|---|---|---|
| NOT RUN | Never run in this folder | `--info` | ○ |
| RUNNING | In progress | `--run` | ◐ (animated) |
| OK | Ran, no FLAG or STOP | `--ok` | ✓ |
| INFO | Ran; informational notes only | `--info` | i |
| FLAG | Ran; warnings to review before relying on output | `--flag` | ! |
| STOP | Failed a STOP check or errored; later stages blocked | `--stop` | ✕ |
| STALE | An input changed after the last run; re-run needed | `--info` hatched | ↻ |

State is never conveyed by colour alone (WCAG 1.4.1). Check codes (e.g. `S07`, `A16`, `W-NR-VALUE`) are shown
verbatim and link to the checks catalogue (§10).

---

## 7. Inputs (MUST)

Carries over the owner's XoL decisions:

- Every input shows: label, **Required / Optional** marker (text label + left-border colour: required = flag colour,
  optional = info colour; never colour alone), help text (what to enter), and either the options (drop-down with each
  option explained) or an example beside free text.
- Validation on leaving the field and before any run; errors listed in an error summary at the top of the section
  with links to the fields; the field shows the message beside it.
- Hide what doesn't apply (rows / columns irrelevant to the chosen adapter, layer type or mode) rather than greying
  out large blocks.
- Two audiences: experienced actuaries and less technical underwriters. Defaults visible; advanced inputs behind
  "Show advanced"; judgement inputs carry a *justification* field.
- Where the input lives in an Excel workbook, the page edits it directly (D-UI6; XoL Control model) through the
  Workbook editor (§5). Open in Excel with change detection (§2.8) remains for workbooks the manifest does not mark
  `editable` (e.g. a mapping workbook a TPA sends back). Never both for the same cell.

---

## 8. Visual theme (MUST use tokens; no literal colours in tool pages)

- **One tokens file** (`gc_tokens.css`, generated from `gc_tokens.json` in DTCG format) shared by all tools. Tool
  pages add no colours, fonts or sizes of their own.
- Palette (kit 0.9.0): navy `#0b2545` (header, headings), teal `#1a8a8a` (primary action, links), ink `#1d2733`,
  background `#f4f6f9`, cards white; status colours ok / flag / stop / info / run with a *soft* background variant.
- **Light theme default; dark theme MUST (D-UI3, owner 2026-11-08, in UI-1.0)** be provided by a second token set
  (`[data-theme="dark"]`), toggle in the header, choice remembered per browser (localStorage, wrapped in try/catch);
  both sets pass the §11 contrast test.
- Type: Segoe UI (system), Consolas for code / commands / file paths. Ramp 12 / 13 / 14 (body) / 16 / 20 px.
  Sentence case for headings and buttons.
- Spacing on a 4 px grid (4, 8, 12, 16, 24, 32). Radius 8 px. One shadow level for cards.
- Numbers: tabular figures in tables; right-aligned; thousands separators; currency code shown once in the column
  header (`Premium (AED)`); percentages to 1 dp unless the tool's spec says otherwise; dates `yyyy-mm-dd`, times
  24-hour.

---

## 9. Content and wording (MUST)

- Plain English, UK spelling, active voice, second person ("Open the Inputs workbook").
- Buttons are verbs + object ("Run 03", "Open in Excel", "Copy prompt"); no "Click here", no "Submit".
- Every message says what happened, why, and what to do next. STOP messages name the file, sheet, column or check.
- One name per thing: terms come from the glossary; a term used in the page but missing from the glossary fails the
  build test (§14).
- No version history in user text ("new in v8"): that belongs in release notes.

---

## 10. Help system (Diátaxis) (MUST)

| Type | Content | Where |
|---|---|---|
| Tutorial | Illustrated guide: first run end to end, screenshots of the real windows (owner's laptop run) | Help → Guide |
| How-to | Short task cards: "Add a new TPA", "Re-run claims only", "Send an admin upload" | Help → How-to; linked from the relevant card |
| Reference | **Glossary**; **input reference** (every workbook sheet / column: required, type, options, example); **checks catalogue** (every code: level, meaning, fix); **file index** (every folder and file the tool reads or writes) | Help → Reference |
| Explanation | Method notes (burning cost, credibility, development factors, endorsement logic) | Help → Explanation |

- **Single source**: help text, glossary, check messages and prompt text each live in one data file per tool
  (JSON / CSV / MD) consumed by the page, the Excel tooltips, the Word/HTML manuals and the LenAI docs. No copy-paste.
- **Glossary schema**: `term`, `definition` (≤ 2 sentences), `aliases`, `category` (data, method, treaty, check,
  file), `used_in` (section / stage anchors), `see_also`, `source` (spec section). Shared actuarial terms
  (burning cost, completion factor, credibility, UWY, member-month…) live in a **common glossary** shipped with the
  kit; tool-specific terms extend it.
- **Index**: generated, not hand-written: every section, card, input, check code, file and glossary term, A–Z with
  anchors.
- **Search** (Ctrl+K / header box): client-side over the index, glossary, how-to titles and check codes; results
  grouped by type; Enter jumps to the anchor.
- **Context help**: every input and every glossary term rendered in the page carries a "?" tip (§5).

---

## 11. Accessibility (WCAG 2.2 AA — the criteria that bite here)

- Contrast ≥ 4.5:1 text, ≥ 3:1 UI components and focus indicators (1.4.3, 1.4.11). Token pairs are tested in the kit.
- Fully keyboard operable: logical tab order, visible focus ring (2px teal outline + offset), no keyboard traps,
  focus not hidden under the sticky header (2.1.1, 2.4.7, 2.4.11).
- Skip link to main content; landmarks (`header`, `nav`, `main`); one `h1`; headings in order (2.4.1, 1.3.1).
- Target size ≥ 24 × 24 px (2.5.8); no drag-only interactions (2.5.7).
- Status changes (run started / finished / STOP) announced via an `aria-live` region (4.1.3).
- Forms: labels tied to inputs, errors identified in text, help available consistently in the same place
  (3.3.1, 3.3.2, 3.2.6).
- Respect `prefers-reduced-motion` (no spinner animation) and 200% zoom (1.4.4, 1.4.10).

---

## 12. State and persistence

- Run state, file times and checks come from the server (files in the output folder) — the source of truth.
- localStorage only for conveniences: theme, collapsed cards, last search; always try/catch; the page works with it
  empty.
- The page never stores client data in the browser.

---

## 13. Data boundary and release

- Page and manifest carry no client names, paths or values; client folders are read at run time only.
- Synthetic / test material appears only in the admin pack (owner decision for XoL and Merit); the production pack's
  page hides the Admin section entirely.
- Pages, kit and server ship inside each tool's release zip; nothing is fetched at run time.

---

## 14. Kit, versioning and tests

- Kit version `UI-x.y` (this standard) and kit build `x.y.z` (CSS / JS / server). Each manifest declares the kit build
  it was tested with; the page shows it in the status bar.
- **Kit location (D-UI1, owner 2026-11-08)**: master in its own **private** repo `mtamsyed-gc/gc-ui-kit` (tokens, CSS,
  JS, generic manifest-driven `serve.py`, common glossary, content and accessibility tests, this standard). Each tool
  vendors a pinned copy into `ui/kit/` with a `VERSION` file (the `treaty_tool` pattern); a per-tool test fails if the
  vendored copy differs from the pinned version's hashes. Tools upgrade the kit on their own release cycle. Seeded
  from xolpricing `ui/kit` 0.9.0 + `tools/ui/serve.py`; xolpricing then vendors it back like any other tool.
- Automated tests per tool (plain Python, standard library + the native pins):
  - server: allow-list, never-delete, one-run-at-a-time, API shapes (XoL `tests/test_ui.py` pattern);
  - content: every glossary term used is defined; every anchor in the index resolves; every check code in the
    workflows has a catalogue entry; every manifest file / command exists in the pack;
  - accessibility lint: token contrast pairs, labels on inputs, one h1, no `alert(` / `confirm(` in JS.
- Laptop check per release: page driven in Chrome on the owner's laptop, screenshots refreshed for the guide.

---

## 15. Release review checklist (Nielsen heuristics + this standard)

| # | Check | Pass when |
|---|---|---|
| H1 | Visibility of system status | Every stage shows a §6 state; runs show live log and elapsed time |
| H2 | Match with the real world | Terms match the glossary and GC / actuarial usage; section numbers match folders |
| H3 | User control and freedom | Stop run, re-run from any stage, cancel on every dialog |
| H4 | Consistency and standards | Kit components only; no literal colours; status words identical across tools |
| H5 | Error prevention | STOP gates downstream stages; STALE detection; confirm before long or overwriting actions |
| H6 | Recognition rather than recall | Commands, prompts and paths are shown with Copy; nothing must be typed from memory |
| H7 | Flexibility and efficiency | Keyboard shortcuts (Ctrl+K search, R run focused stage), run from / to |
| H8 | Aesthetic and minimalist design | Admin hidden by default; advanced inputs collapsed |
| H9 | Help users recover from errors | Every STOP says the file / field / check and the fix, linking to the catalogue |
| H10 | Help and documentation | Guide, how-to, glossary, index, search reachable from every screen |
| A11 | WCAG 2.2 AA | §11 items pass the kit lint and a manual keyboard pass |

---

## 16. Open questions for the owner

- ~~Q1 Kit home~~ → decided D-UI1 (§14).
- ~~Q2 Merit launcher~~ → decided D-UI2 (§2.7). Merit gets one `00_Start_Here\00_Merit_UI.cmd` that starts the
  server; the numbered launchers stay as they are.
- ~~Q3 Dark theme~~ → D-UI3: in UI-1.0 (§8).
- ~~Q4 LenAI prompt cards~~ → D-UI4: the page prepares a ready LenAI folder (§5).
- ~~Q5 Power BI~~ → D-UI5: open + last refresh tile only (§5).
- ~~Q6 Excel editing~~ → D-UI6: in-page editing with the §2.4 write rule (backup, lock refusal).

No open questions at UI-0.3.
