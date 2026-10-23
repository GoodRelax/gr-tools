// UI tests for the built claim chart, run in headless Chromium.
//
//   node tests/ui.test.js
//
// Needs Playwright (and Ajv for the schema checks). Set CC_NODE_MODULES to a node_modules folder
// that has them if they are not installed next to this file. The samples are built first.
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const NM = process.env.CC_NODE_MODULES || "";
const need = (name) => require(NM ? path.join(NM, name) : name);
const { chromium } = need("playwright");
const Ajv = need("ajv/dist/2020").default;

const OUT = fs.mkdtempSync(path.join(os.tmpdir(), "claim-chart-ui-"));
const US = path.join(OUT, "us.html");   // the two public samples
const FX = path.join(OUT, "fx.html");   // a made-up claim with a NOT, a reference and an optional clause
const SRC = {
  US5946647: path.join(ROOT, "samples", "src-US5946647"),
  US8046721: path.join(ROOT, "samples", "src-US8046721"),
  XX0000001: path.join(ROOT, "tests", "fixtures", "src-XX0000001"),
};
const python = process.env.PYTHON || "python";
const build = path.join(ROOT, "scripts", "build.py");
execFileSync(python, ["-I", build, US, SRC.US5946647, SRC.US8046721]);
execFileSync(python, ["-I", build, FX, SRC.XX0000001]);

let failed = 0;
function check(name, ok, detail) {
  console.log((ok ? "ok    " : "FAIL  ") + name + (ok || detail === undefined ? "" : "\n      " + JSON.stringify(detail)));
  if (!ok) failed++;
}
const url = (f) => "file:///" + f.replace(/\\/g, "/");
const ajv = new Ajv({ strict: false, allErrors: true });
const schema = (name) => ajv.compile(JSON.parse(fs.readFileSync(path.join(ROOT, "schema", name), "utf8")));

(async () => {
  // ---- input files follow their schemas
  const inputs = { "tree.json": schema("tree.schema.json"), "ai.json": schema("ai.schema.json"), "meta.json": schema("meta.schema.json"),
    "tr.ja.json": schema("translation.schema.json") };
  for (const [id, dir] of Object.entries(SRC)) {
    for (const [file, validate] of Object.entries(inputs)) {
      const f = path.join(dir, file);
      if (!fs.existsSync(f)) continue;
      check("schema: " + id + "/" + file, validate(JSON.parse(fs.readFileSync(f, "utf8"))), validate.errors && validate.errors.slice(0, 2));
    }
  }

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 }, acceptDownloads: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("dialog", (d) => d.accept());
  await page.goto(url(US));
  const row = (pid, id) => '.row[data-k="' + pid + ":" + id + '"]';
  // claim verdicts of the open tab as one letter each: T(rue) F(alse) U (TBD) N (No need)
  const badges = () => page.$$eval(".claim > h3", (hs) => hs.map((h) =>
    ({ True: "T", False: "F", TBD: "U", "No need": "N" }[h.querySelector(".badge").textContent])).join(""));
  const A = "US5946647", B = "US8046721";

  // ---- overview and jumping
  check("overview is the first and active tab", await page.$eval(".tab", (b) => b.classList.contains("on") && b.dataset.arg === "*"));
  check("AI verdicts per patent", (await page.$$eval('td[data-act="jump"][data-arg$="|0|ai"] .badge', (b) => b.map((x) => x.textContent).join(","))) === "True,False");
  await page.click('td[data-act="jump"][data-arg="' + A + '|3|ai"]');
  check("jump opens the patent in the clicked layer", (await page.$eval(".tab.on", (b) => b.textContent)) === A &&
    (await page.$eval('.seg button.on[data-act="view"]', (b) => b.dataset.arg)) === "ai");
  check("jump scrolls the claim under the header", await page.evaluate(() => {
    const top = document.getElementById("claim-US5946647-3").getBoundingClientRect().top;
    return Math.abs(top - document.getElementById("hd").offsetHeight) < 12;
  }));
  check("jump leaves no outline on rows", (await page.$$(".row.pick")).length === 0);
  await page.click('.seg button[data-arg="user"]');

  // ---- tree text: translation by colour only, no labels, no sentence lines
  check("no per-row translation labels", (await page.$$(".trtag")).length === 0);
  check("no machine-translation tag in the claim text panes", !(await page.$$eval(".otool", (x) => x.some((e) => e.textContent.includes("機械訳")))));
  check("the disclaimer says translations are machine translations", (await page.$eval(".disc", (x) => x.textContent)).includes("訳は機械訳（参考）。最終的な判定は"));
  check("no sentence lines in the US samples", (await page.$$(".ie")).length === 0);
  const tx = (id) => page.$eval(row(A, id) + " .tx", (x) => ({ main: x.firstChild.textContent, trc: x.querySelectorAll(".trc").length }));
  check("both: original first, translation under it", JSON.stringify(await tx("1E.1.2")) === JSON.stringify({ main: "the output device", trc: 1 }), await tx("1E.1.2"));
  await page.check('input[data-act="text"][value="tr"]');
  check("tr: the translation replaces the original", (await page.$eval(row(A, "1E.1.2") + " .tx", (x) => x.innerText.trim())) === "出力装置");
  await page.check('input[data-act="text"][value="orig"]');
  check("orig: no translation in the tree", (await page.$$("#claim-" + A + "-1 .chart .trc")).length === 0);
  check("orig: the claim text can be edited", (await page.$$('#claim-' + A + '-1 button[data-act="editText"]')).length === 1);
  const okText = () => page.$eval('[data-okfor="' + A + ':1"]', (x) => x.textContent);
  check("a matching claim text shows nothing", (await okText()) === "");
  await page.click('#claim-' + A + '-1 button[data-act="editText"]');
  const ta = '#claim-' + A + '-1 textarea.oedit';
  const original = await page.$eval(ta, (x) => x.value);
  await page.fill(ta, original.replace(" comprising:", "\n      comprising:"));
  check("whitespace edits still match and show nothing", (await okText()) === "");
  await page.fill(ta, original.replace("input device", "input unit"));
  check("a changed word shows the mismatch", (await okText()).startsWith("✗"));
  await page.fill(ta, original);
  await page.click('#claim-' + A + '-1 button[data-act="editText"]');
  await page.check('input[data-act="text"][value="both"]');
  const pane = "#claim-" + A + "-1 .otext";
  check("both: one translated line per claim line", (await page.$$(pane + " .trc")).length === 8 && (await page.$$(pane + " span[data-off]:not(.trc)")).length === 8);

  // ---- claim text <-> tree
  await page.evaluate(() => window.scrollTo(0, 0));
  const line6 = (await page.$$(pane + " span[data-off]:not(.trc)"))[6];
  const bb = await line6.boundingBox();
  await page.mouse.click(bb.x + 30, bb.y + 5);
  check("clicking claim text selects the node under it", (await page.$eval(".row.hl", (r) => r.dataset.k)) === A + ":1D.1.3");
  check("the selected node is marked in the claim text", (await page.$eval(pane + " mark", (m) => m.textContent)).startsWith("an action processor"));

  // ---- checks, references, No need
  await page.click(row(A, "1D.1.1") + ' button[data-arg="F"]');
  check("False on the analyzer server makes claims 1-12 False", (await badges()).slice(0, 12) === "FFFFFFFFFFFF", await badges());
  check("rows decided by a sibling show No need", (await page.$$(".row.v-N")).length > 0);
  const before = (await page.$$(".row")).length;
  await page.uncheck('input[data-act="filter"][data-arg="N"]');
  check("hiding No need removes rows", (await page.$$(".row")).length < before);
  await page.check('input[data-act="filter"][data-arg="N"]');
  await page.click('#claim-' + A + '-1 button[data-act="resetClaim"]');
  check("reset claim 1 back to TBD", (await badges())[0] === "U", await badges());

  // ---- AI layer
  await page.click('.seg button[data-arg="ai"]');
  check("AI view: banner and read-only buttons", (await page.$$(".banner")).length === 1 && await page.$eval(row(A, "1A") + " .ck button", (b) => b.disabled));
  check("AI view: claims 13 and 15 True", (await badges())[12] === "T" && (await badges())[14] === "T", await badges());
  await page.uncheck('input[data-act="aiReason"]');
  check("AI reasons can be hidden", (await page.$$(".ai")).length === 0);
  await page.check('input[data-act="aiReason"]');
  await page.click('#claim-' + A + '-13 button[data-act="adoptClaim"]');
  check("adopting claim 13 makes the person's claim 13 True", (await badges())[12] === "T" && (await page.$eval('.seg button.on[data-act="view"]', (b) => b.dataset.arg)) === "user");

  // ---- box height fits its content; bars
  const fit = (n) => page.$eval("#claim-" + A + "-" + n + " .cbody", (b) => {
    const c = b.querySelector(".chart"), i = b.querySelector(".orig .inner");
    return { box: b.getBoundingClientRect().height, need: Math.max(c.scrollHeight, i.scrollHeight + 8), scrolls: c.scrollHeight > c.clientHeight + 1, cls: b.className };
  });
  let f = await fit(2);
  check("claim box fits its content", !f.scrolls && Math.abs(f.box - f.need) < 12, f);
  const bar = await page.$("#claim-" + A + "-1 .bar-bottom");
  await bar.evaluate((e) => e.scrollIntoView({ block: "center" })); // not under the sticky header
  let r = await bar.boundingBox();
  await page.mouse.move(r.x + 300, r.y + 3); await page.mouse.down(); await page.mouse.move(r.x + 300, r.y - 400, { steps: 5 }); await page.mouse.up();
  f = await fit(1);
  check("dragging the bottom bar fixes the height", f.cls.includes("fixed") && f.scrolls, f);
  const bar2 = await page.$("#claim-" + A + "-1 .bar-bottom");
  await bar2.evaluate((e) => e.scrollIntoView({ block: "center" }));
  r = await bar2.boundingBox();
  await page.mouse.dblclick(r.x + 300, r.y + 3);
  check("double-click fits again", !(await fit(1)).cls.includes("fixed"));

  // ---- look
  await page.fill('input[data-act="fs"]', "25"); await page.press('input[data-act="fs"]', "Enter");
  check("font size is clamped to 20px", (await page.evaluate(() => getComputedStyle(document.body).fontSize)) === "20px");
  await page.fill('input[data-act="fs"]', "14"); await page.press('input[data-act="fs"]', "Enter");
  await page.selectOption('select[data-act="theme"]', "dark");
  check("dark theme", (await page.evaluate(() => document.documentElement.dataset.theme)) === "dark");
  await page.selectOption('select[data-act="theme"]', "light");
  await page.selectOption('select[data-act="menuLang"]', "en");
  check("menu language changes the controls only", (await page.$eval('button[data-act="expandAll"]', (b) => b.textContent)) === "Expand all");
  await page.selectOption('select[data-act="menuLang"]', "ja");
  await page.check('input[data-act="layout"][value="tb"]');
  check("stacked layout", await page.evaluate(() => document.body.classList.contains("tb")));
  await page.check('input[data-act="layout"][value="lr"]');

  // ---- JSON out and back in, HTML save and reopen
  await page.click(row(A, "1B") + ' button[data-act="memo"]');
  await page.fill('textarea[data-act="memoInput"]', "input via keyboard");
  await page.click("#hd");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click('button[data-act="exportJson"]')]);
  const jp = path.join(OUT, "out.json");
  await dl.saveAs(jp);
  const doc = JSON.parse(fs.readFileSync(jp, "utf8"));
  const validateResult = schema("claim-chart-result.schema.json");
  check("exported JSON follows its schema", validateResult(doc), validateResult.errors && validateResult.errors.slice(0, 2));
  const c1 = doc.patents.find((x) => x.id === B).claims[0].nodes;
  c1.find((n) => n.id === "1B").check = "false";
  c1.find((n) => n.id === "1D").text = "tampered";
  c1.find((n) => n.id === "1D").check = "true";
  fs.writeFileSync(path.join(OUT, "in.json"), JSON.stringify(doc));
  const p2 = await browser.newPage({ viewport: { width: 1500, height: 950 }, acceptDownloads: true });
  p2.on("pageerror", (e) => errors.push("p2: " + e));
  await p2.goto(url(US));
  await p2.setInputFiles("#jsonFile", path.join(OUT, "in.json"));
  await p2.waitForTimeout(300);
  check("import reports skipped text", /1 件は原文が合わず/.test(await p2.$eval("#toast", (x) => x.textContent)), await p2.$eval("#toast", (x) => x.textContent));
  await p2.click('button[data-arg="' + B + '"]');
  check("imported check applies", (await p2.$eval(row(B, "1B") + " .ck button.on", (b) => b.dataset.arg)) === "F");
  const [dl2] = await Promise.all([p2.waitForEvent("download"), p2.click('button[data-act="save"]')]);
  const saved = path.join(OUT, "saved.html");
  await dl2.saveAs(saved);
  const p3 = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  p3.on("pageerror", (e) => errors.push("p3: " + e));
  await p3.goto(url(saved));
  check("a saved page reopens where it was", (await p3.$eval(".tab.on", (b) => b.textContent)) === B &&
    (await p3.$eval(row(B, "1B") + " .ck button.on", (b) => b.dataset.arg)) === "F");
  check("memos survive export, import and save", (await p3.$eval('button[data-arg="' + A + '"]', (b) => (b.click(), true))) &&
    (await p3.$eval(row(A, "1B"), (r) => r.textContent.includes("input via keyboard"))));

  // ---- the made-up claim: a negation, a reference, an optional clause
  const X = "XX0000001";
  const p4 = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  p4.on("pageerror", (e) => errors.push("p4: " + e));
  await p4.goto(url(FX));
  await p4.click('button[data-arg="' + X + '"]');
  check("leaf under NOT shows its i.e. sentence", (await p4.$eval(row(X, "1C.1.1.1") + " .ie", (x) => x.textContent)) === "i.e., 特定の通信規格に依存しない");
  check("list under NOT is shown as OR→AND", (await p4.$eval(row(X, "1C.1.1") + " .g", (x) => x.textContent)) === "OR→AND");
  check("an optional clause is always True", (await p4.$eval(row(X, "2C"), (x) => x.className)).includes("v-T"));
  await p4.click(row(X, "1C.1.1.1") + ' button[data-arg="F"]');
  check("False under NOT makes the element False", (await p4.$eval(row(X, "1C"), (x) => x.className)).includes("v-F"));
  check("a citing claim mirrors the cited claim", (await p4.$$eval(".claim > h3", (h) => h.map((x) => x.querySelector(".badge").textContent).join(","))) === "False,False");

  check("no page errors", errors.length === 0, errors);
  await browser.close();
  console.log(failed ? "\n" + failed + " failed" : "\nall passed");
  process.exit(failed ? 1 : 0);
})();
