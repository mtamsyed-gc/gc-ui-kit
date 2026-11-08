# gc-ui-kit — standing instructions for Claude

- `UI_STANDARD.md` is the standard every tool page follows; a change to the standard is a version bump of that file
  (UI-x.y) and is mirrored to ete-dashboard `docs/UI_STANDARD.md`.
- Kit builds are `x.y.z` in `VERSION`. Any change under `kit/` bumps the patch at least; a manifest-schema change bumps
  the minor and is noted in `README.md`.
- Tokens: edit `kit/gc_tokens.json`, then `py tools/build_tokens.py`. Never edit `gc_tokens.css` by hand. No literal
  colours in `gc_ui.css` (the tests fail).
- Server: standard library only (openpyxl only inside workbook functions). Never delete a user file. Writes only the
  editable workbooks (with backup), LenAI folders and the state dir.
- Tests: `py tests/test_kit.py` before every commit. Synthetic data only.
- Vendoring: tools consume the kit through `tools/vendor.py`; never edit a vendored copy inside a tool.
