# Finding candidate patents (entry ①)

Goal: a short list of patents worth charting, chosen by the person. A search is never complete;
say what was and was not searched.

## Steps

1. **Read the target** (spec or code) and list its distinctive functions in plain words, each with
   the file and section it comes from. Ask the user to confirm or trim the list before searching.
2. **Build queries** per function: 2–4 key terms plus synonyms, in the language of each office
   (Japanese for JP, English for US/EP/IN, Chinese for CN). Add classification codes when they are
   obvious (e.g. G06Q 10/06 for scheduling, G06F 3/048 for touch interfaces).
3. **Search** each chosen office (J-PlatPat for JP, Google Patents or USPTO for US, Espacenet for EP,
   CNIPA or Google Patents for CN, InPASS for IN). Keep the first ~50 results per query; skip
   applications that were refused or withdrawn and, if the user asked, rights that have lapsed.
4. **Screen** by reading claim 1 (the independent claims) of each hit against the function list.
   Keep a hit only if most elements of an independent claim plausibly match.
5. **Write `candidates.md`** in the output folder:

   | # | Office, number (holder, filed, status, expiry estimate) | Claim 1 in short | Target functions it touches | First impression | Notes |
   |---|---|---|---|---|---|

   "First impression" is one of: likely close / depends on use / likely clear — never a verdict.
6. **Ask the user which to chart.** Then follow the main workflow for each chosen patent.

## Limits to report

- Applications are published about 18 months after filing; recent ones cannot be found.
- Keyword search misses patents that use other words; classification search helps but is not complete.
- Status shown by search sites (Google's "Active", "Expired") is an estimate; check the office
  register for anything that matters.
