# gc-ui-kit — the shared UI kit for GC tool front ends

Kit 1.2.2 implements the **GC Tools UI Standard** (`UI_STANDARD.md`, UI-0.3) for every browser page of the owner's GC
tools: Merit (first adopter of this kit), the XoL pricing tool (0.9.1, kit 1.1.1), TSM (TW-1.2, kit 1.2.0), the
pricing workbench. Private repository; the kit ships inside each tool's release pack.

## What is here

| Path | What |
|---|---|
| `kit/gc_tokens.json` | Design tokens (W3C DTCG format): light and dark sets + the contrast pairs the tests check |
| `kit/gc_tokens.css` | Generated from the JSON by `tools/build_tokens.py` (never edited by hand) |
| `kit/gc_ui.css` | Components: shell (header, index, status bar), cards, pills, buttons, banners, tables, sheet editor, log, dialogs, search, help panel |
| `kit/gc_ui.js` | Behaviour: shell builder, state polling, components, workbook editor (D-UI6), LenAI prompt cards (D-UI4), search (Ctrl+K), glossary / index, theme (D-UI3), offline fallback |
| `kit/gc_server.py` | The local server (standard library): static files, state, runs of manifest-declared launchers (D-UI2), tables, workbook read / save with backup and lock refusal (§2.4), LenAI folders, docs |
| `kit/common_glossary.json` | The shared actuarial / reinsurance glossary; a tool's glossary extends or overrides it |
| `tools/vendor.py` | Copies the kit into `<tool>/ui/kit` with `VERSION` and `HASHES.json`; `--check` fails on a hand edit |
| `tools/build_tokens.py` | Builds the CSS from the JSON and checks every contrast pair |
| `tests/test_kit.py` | Tokens, JS lint, glossary schema, the server on a fake tool, vendoring |

## How a tool uses it

1. `py tools/vendor.py <tool>/ui/kit` (from this repo). The tool's tests call `vendor.check()` on the copy.
2. The tool adds `ui/<tool>/manifest.json`, `index.html`, a small `plugin.py` (tool state) and `glossary.json`.
3. A launcher (`.cmd`) runs `py ui/kit/gc_server.py --manifest ui/<tool>/manifest.json --client <folder> --port <tool port>`.

Ports: XoL 8765, Merit 8766, TSM 8767, workbench 8768.

## Manifest schema notes

- 1.2.2 fix (no manifest change; `/api/sheet` adds fields): a column whose rows carry different validation lists gets `row_options` = `[[first row, last row, set]]` into the sheet's `option_sets`, and the editor offers each row its own list (Merit's Columns tab: the claims list on claims rows, the premium list on premium rows; the Values tab: each field's standards). A list Excel lets the user type past (no error alert, or a warning / information alert) is `free`: the editor shows a text box with the list as suggestions (`<datalist>`), so every value Excel accepts can be entered in the page too (a value not in the list, two fields `a; b`); a strict list (stop alert) stays a drop-down. A list that covers only some rows of a column (Merit's Run settings: CSV / Parquet on the Collated input row) is offered on those rows only; before 1.2.2 every row of the column got it, so a date or number could not be typed on the other rows. One page per port: the server no longer sets SO_REUSEADDR (on Windows it takes the port with SO_EXCLUSIVEADDRUSE), so a second page started on a busy port moves to a free one; before 1.2.2 Windows let both bind and the browser kept reaching the first page, another client folder's (found on the laptop). `POST /api/open {path: "."}` opens the client folder itself (before: refused as outside the roots); the Open toast reads "Opened <what>". Found by Merit's browser test: 15 Values-tab standards and two two-field mappings of the demo client's answer key could not be entered in the page.
- 1.2.1 fix (no schema change): `runButton` awaits an `args` function, so a dialog's answers reach the launcher and the run starts only once the dialog is answered; `null` (Cancel) starts no run. Before 1.2.1 an async dialog's run started at the click with args `{}` and the answers were dropped (found on Merit's Intake profile: the payer typed was ignored). Every tool page with an args dialog (Merit, XoL, TSM) must re-vendor. Test: `tests/js_runbutton.js`.
- 1.2.0: a plugin may define `workbooks(tool)` returning extra `editable_workbooks` entries discovered at run time (same schema; a manifest id wins on a clash) — for tools whose editable files are one per client folder; a positional action arg may carry `"rel_path": true` (the page gives a path relative to the client folder, the server checks it is an existing file inside the allowed roots and passes it absolute); an action may carry `"env": {NAME: value}` with `{client}`, `{ui}`, `{page}` substituted; `sheet_help` may return `value_cols` (a list) when one key column's help applies to several value columns (a scenario grid); `"doc_root": "{ui}/.."` serves `/doc/<file>` from the tool's own folder when the client folder holds data only.
- 1.2.0 fix: in a key-value sheet with `rows_help`, a row's options are its own (previously a row without options inherited the column's, taken from another row's validation).
- 1.1.1: `GET /api/plugin/<name>` calls the plugin's `api_<name>(tool, query)` (read-only tool routes).
- 1.1.0: a plugin may define `sheet_help(tool, wid, sheet, columns)` returning refined `columns` (description, required, options, example, kind), per-row help (`rows_help` keyed by the value of `key_col`, applied to `value_col`) and a sheet `note`; blue fill `DDEBF7` = an optional input (kind `optional`); `POST /api/copy {path}` saves a timestamped copy of an allowed file.

## Rules

- Tokens, not literal colours. Components from the kit, not hand-rolled variants.
- Change the kit here, bump `VERSION`, run `tests/test_kit.py`, then re-vendor into each tool on its own release cycle.
- No network, no CDN, no client data in the page or the manifest. Synthetic data only in tests.

## Tests

    py tests/test_kit.py
    py tools/build_tokens.py --check
