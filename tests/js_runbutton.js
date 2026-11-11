// Behaviour test for GC.runButton (kit 1.2.1): the run waits for an async args dialog, sends its answers, and does not
// start when the dialog is cancelled. Run by tests/test_kit.py with node; a minimal fake DOM, no packages.
"use strict";
const fs = require("fs");
const path = require("path");

class Node_ {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.children = []; this.attrs = {}; this.listeners = {};
    this.style = {}; this.dataset = {}; this.classList = { add() {}, remove() {}, toggle() {}, contains() { return false; } };
    this.nodeType = 1; this.textContent = ""; this.className = ""; this.disabled = false; this.title = ""; }
  setAttribute(k, v) { this.attrs[k] = v; }
  getAttribute(k) { return this.attrs[k]; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
  removeEventListener(t, f) { this.listeners[t] = (this.listeners[t] || []).filter((g) => g !== f); }
  append(...c) { this.children.push(...c); }
  appendChild(c) { this.children.push(c); return c; }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  remove() {}
}
const doc = new Node_("document");
doc.createElement = (t) => new Node_(t);
doc.createTextNode = (s) => ({ nodeType: 3, textContent: s });
doc.body = new Node_("body");
doc.documentElement = new Node_("html");
global.document = doc;
global.window = global;
global.localStorage = { getItem() { return null; }, setItem() {} };
const sent = [];
global.fetch = async (url, init) => { sent.push({ url, body: init && init.body ? JSON.parse(init.body) : null });
  return { ok: true, json: async () => ({ run: { id: "r1" } }) }; };

const src = fs.readFileSync(path.join(__dirname, "..", "kit", "gc_ui.js"), "utf8");
new Function(src)();
const GC = global.GC;

function click(b) { return Promise.all((b.listeners.click || []).map((f) => f())); }
const fail = (m) => { console.error("FAIL " + m); process.exit(1); };

(async () => {
  // 1. async dialog: nothing is sent before it is answered; its answers are sent
  let answer;
  const pending = new Promise((r) => { answer = r; });
  const b1 = GC.runButton("profile", { args: () => pending });
  const done = click(b1);
  await new Promise((r) => setTimeout(r, 20));
  if (sent.length) fail("run started before the dialog was answered: " + JSON.stringify(sent));
  answer({ payer: "AETM" });
  await done;
  if (sent.length !== 1) fail("expected one run, got " + sent.length);
  if (JSON.stringify(sent[0].body) !== JSON.stringify({ action: "profile", args: { payer: "AETM" } })) fail("args sent: " + JSON.stringify(sent[0].body));
  // 2. cancelled dialog (null): no run
  sent.length = 0;
  await click(GC.runButton("profile", { args: async () => null }));
  if (sent.length) fail("a cancelled dialog started a run");
  // 3. plain object and no args: unchanged behaviour
  await click(GC.runButton("values", { args: { a: "1" } }));
  await click(GC.runButton("values", {}));
  if (JSON.stringify(sent.map((s) => s.body.args)) !== JSON.stringify([{ a: "1" }, {}])) fail("object / no args: " + JSON.stringify(sent));
  console.log("runButton OK");
})().catch((e) => fail(e.stack || e));
