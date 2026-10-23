# AI provisional checks (`ai.json`)

The AI's answers are a separate layer. The page shows them only when "Show AI provisional" is on,
marks them as unconfirmed, and copies them into the person's answers only when the person presses
"Adopt". Format: `schema/ai.schema.json`.

```json
{
  "target": "Sample device spec (made up), samples/target-sample/device-spec.md @ <repo> <branch> <commit>",
  "by": "<model name> (AI provisional checks)",
  "date": "YYYY-MM-DD",
  "base": "..",
  "judgments": {
    "1B": {"check": "false",
           "reason": "Decisive. The lock screen shows no unlock image, so no contact on it is detected.",
           "evidence": [{"file": "target-sample/device-spec.md", "quote": "鍵や矢印の絵は出さない。"}]}
  }
}
```

- `base` is the folder that `evidence[].file` is relative to, relative to the source folder.
- Only leaves and `own` nodes take a check (the build refuses others).
- Write `reason` in the user's language.

## How to judge

1. **Decisive first.** A claim is False as soon as one required element is False. For each claim,
   look first for an element the target clearly does not meet, and give it `false` with evidence.
   Its siblings then become "No need", so the person reads only the decisive rows.
2. **Evidence is a verbatim quote** from the target (spec, code, manual). The build looks for it in
   the file (ignoring whitespace) and computes the line number; a quote that is not there stops the
   build. Quote enough to be unambiguous, not whole sections.
3. **No description is not "no".** If the target does not say, answer `tbd` and write
   "not described" in `reason`. Never infer `false` from silence.
4. **Interpretation stays visible.** When the answer depends on how a word is read (claim
   construction, means-plus-function, "specific", "separate"), say so in `reason`; prefer `tbd`
   over a confident guess. If you cite a court decision from memory, say that it is from memory.
5. **Leaves under a NOT** answer their "i.e." sentence: `true` means the product satisfies the
   negated sentence ("does not depend on X").
6. **Record the target's version.** Specs and code change; the quote and its line number are only
   true for one version. Put repository, branch and commit (or file date) into `target`.

## Updating later

The person may export JSON from the page, have an AI change `aiCheck`, `aiReason` and `aiEvidence`,
and import it again. Imported AI answers are marked "quotes not verified" because only the build can
check quotes; to verify them, copy them back into `ai.json` and build.
