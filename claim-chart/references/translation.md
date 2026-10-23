# Machine translation (`tr.<lang>.json`)

A translation is a reading aid next to the original, never a replacement: the person checks the
original. The page shows it in a different colour, and the disclaimer says once that translations
are machine translations. Format: `schema/translation.schema.json`. `<lang>` is `ja` or `en`.

```json
{
  "nodes":   {"1A": "…", "1D.1.1": "アナライザーサーバー ［1D.1.1.1］;"},
  "lines":   {"1": ["line 1 of claim 1", "line 2", "…"], "2": ["…"]},
  "summary": {"problem": ["heading", "paragraph 1", "…"], "solution": ["…"]}
}
```

| Part | Rule (checked by the build) |
|---|---|
| `nodes` | the node's own wording; each child appears as its hole `［label］` exactly once, no other holes. Leaves and references have no holes. Plain AND/OR lists may be left out. |
| `lines` | one entry per line of the claim body, in order (shown in the claim text pane) |
| `summary` | the heading, then one entry per paragraph of that summary file |

Translate faithfully: keep terms consistent within a patent (the same English term gets the same
Japanese term everywhere), keep "前記 / said / the" references, and add nothing that is not in the
original — no explanations, no notes.
