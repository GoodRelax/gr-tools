# Getting the original text

The claims and summary must be byte-for-byte what the publication shows. Copy them out of the page
mechanically, then prove the copy: compute SHA-256 of the same string in the page and of the file,
and compare. Never retype from memory or from a summary.

| Office | Source | Status |
|---|---|---|
| JP | J-PlatPat | verified 2026-10-23 (two patents) |
| US | Google Patents | verified 2026-10-23 (two patents) |
| EP | Espacenet / EP Register | not yet verified — verify on first use and update this file |
| CN | CNIPA / Google Patents | not yet verified |
| IN | InPASS | not yet verified |

The browser: J-PlatPat runs on JavaScript, so plain HTTP fetching does not see the text. Use a real
browser (the app's built-in browser, or the user's browser through an extension) and run the
snippets below in the page.

## Moving long text out of the page without retyping

Return the text from the page script. If the tool saves long results to a file instead of showing
them, write the file from that saved result with a script. If you have to transcribe, the SHA-256
comparison below is mandatory and catches every slip.

```js
// in the page: hash a string the same way Python does (UTF-8)
const sha = async (s) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)))]
  .map((x) => x.toString(16).padStart(2, "0")).join("");
```

```python
import hashlib; hashlib.sha256(text.encode("utf-8")).hexdigest()
```

Compare the length too. Write files with LF line endings and a final newline (the build strips
trailing whitespace before splitting).

## JP — J-PlatPat

1. Open the fixed address `https://www.j-platpat.inpit.go.jp/c1801/PU/JP-<number>/15/ja`
   (e.g. `JP-0000000` for patent 0000000). It shows a one-row result list.
2. The number link opens the document in a new tab, which a controlled browser may block. Capture
   the address instead, then open it in the same tab (the state lives in the tab's session):

   ```js
   window.open = (u) => { window.__u = u; return null; };
   [...document.querySelectorAll("a")].find((a) => a.textContent.trim() === "特許<number>").click();
   window.__u   // "/p0200"
   ```

   Navigate the same tab to `https://www.j-platpat.inpit.go.jp/p0200`.
3. Open the collapsed sections (claims, description):

   ```js
   for (const e of [...document.querySelectorAll("a.l-toggle__header")].filter((e) => e.innerText.includes("開く"))) {
     e.click(); await new Promise((r) => setTimeout(r, 3000));
   }
   ```

4. Cut the parts out of `document.body.innerText`:

   ```js
   const t = document.body.innerText;
   const cut = (s, e) => { const x = t.indexOf(s); const y = t.indexOf(e, x + 1); return t.slice(x, y).replace(/\s+$/, ""); };
   const claims = cut("【請求項１】", "詳細な説明");
   const problem = cut("【発明が解決しようとする課題】", "【課題を解決するための手段】");
   const solution = cut("【課題を解決するための手段】", "【発明の効果】");
   const effect = cut("【発明の効果】", "【図面の簡単な説明】");
   ```

5. **Invisible characters.** Some publications indent every line with two U+00A0 (no-break space).
   Count them before copying: `(s.match(/ /g) || []).length`. Keep them in the files (the
   tree must contain them too, usually as glue at the start of each line).
6. Bibliographic data (number, title, holder, filing and registration dates, status) is at the top of
   the same page; the status line ("特許 有効" etc.) is on the result list of step 1.

## US — Google Patents

The page is large; read it with `fetch` from any `patents.google.com` page instead of rendering it.

```js
const norm = (s) => s.replace(/\s+/g, " ").trim();
function ownText(el) {          // a claim-text element's own text; nested claim-texts become breaks
  let s = "";
  for (const n of el.childNodes) {
    if (n.nodeType === 3) s += n.textContent;
    else if (n.nodeType === 1 && !(n.classList.contains("claim-text") || n.classList.contains("claim"))) s += n.textContent;
    else if (n.nodeType === 1) s += "\u0001";
  }
  return s;
}
const d = new DOMParser().parseFromString(await (await fetch("/patent/US5946647A/en")).text(), "text/html");
const top = [...d.querySelector('section[itemprop="claims"]').querySelectorAll("div.claim[num]")]
  .filter((c) => !c.parentElement.closest("div.claim[num]"));
const claims = top.map((c) => {
  const lines = [];
  for (const ct of c.querySelectorAll("div.claim-text"))
    for (const piece of ownText(ct).split("\u0001")) { const x = norm(piece); if (x) lines.push(x); }
  return lines;
});
// claims.txt: "1." on its own line, then the lines with the leading "1. " removed
const claimsTxt = claims.map((ls) => { const m = ls[0].match(/^(\d+)\.\s+/); return m[1] + ".\n" + [ls[0].slice(m[0].length), ...ls.slice(1)].join("\n"); }).join("\n");
```

- Whitespace is normalised (runs of spaces become one) and each `claim-text` element becomes one
  line. This is a fixed, mechanical rule; record it in `meta.json` `status` or `source` if it matters.
- Summary sections: walk `section[itemprop="description"]` in order; a `heading` element starts a
  section and each `div.description-paragraph` is one paragraph. Use the sections whose heading
  starts with `BACKGROUND` (role `problem`) and `SUMMARY` (role `solution`). US patents rarely have
  an "effects" section; leave it out.
- Status and dates: `[itemprop="legalStatusIfi"]` ("Expired - Lifetime", "Active"),
  `meta[name="DC.date"]`, `meta[name="DC.contributor"]` (inventors, then the assignee). Google's
  status is an estimate; say so in `status`.
- Google Patents sometimes answers 503 after many requests; wait, or use the USPTO full text.

## Pasted text (entry ③)

The paste is the original. Save it unchanged as `claims.txt` (with header lines as in the paste)
and say in `meta.json` `source` that it was pasted, and when.
