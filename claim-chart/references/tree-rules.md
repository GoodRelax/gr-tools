# Splitting claims into trees (`tree.json`)

`tree.json` is `{"claims": [<tree of claim 1>, <tree of claim 2>, ...]}` in claim order
(`schema/tree.schema.json`). A tree is made of **glue** (plain strings: claim text that is not a
condition by itself) and **nodes**:

| Node | Meaning |
|---|---|
| `{"L": "text"}` | leaf: a condition the person marks True / False / TBD |
| `{"A": [...]}` / `{"O": [...]}` | AND / OR over the parts |
| `{"N": [...]}` | NOT over exactly one plain `A` / `O` list of leaves |
| `{"P": "text"}` | optional clause: always True |
| `{"R": n, "t": "text"}` | reference to an earlier claim n |
| `"own": true` | on `A` / `O`: the node's own wording (its glue) is a condition too, and takes a check |
| `"alt": true` | on `A` / `O`: the scope reads two ways; the person may switch AND / OR |

**Joining every string of a tree in order must give the claim body exactly** — including line breaks,
spaces, punctuation and invisible characters. The build checks this and prints the first difference.

## The rules

They are mechanical so that two people splitting the same claim get the same tree.

1. A claim is an `A`. The preamble ("…であって、", "…, comprising:", "…において、") is a leaf.
2. Each element (clause ending with "と、", "し、", "であり、", ";", "; and") is a child of that `A`.
   Line breaks and connecting words between elements are glue.
3. Inside an element, a list joined by "又は / 若しくは / or / at least one of / のいずれか" is an `O`;
   joined by "及び / 並びに / and / かつ" is an `A`. Separators ("、", ", ", " or ") are glue of the list.
   If the element has wording of its own besides the list, the element is `own`.
   Two items that are together the object of one act ("selection of a structure and a linked action")
   stay in one leaf.
4. A negation that wraps **one** list is an `N` over that list. Its leaves are read as negated
   sentences — the build adds "i.e., …" to each — and the list's gate flips (De Morgan).
   A negation over two or more lists stays one leaf.
5. A clause with a condition ("…場合に限り", "…場合に", "…ときは", "if …", "when …") is one leaf,
   lists included. Exception: when the condition is nothing but a list of events ("detecting at
   least one of A, B and C"), make it an `O` with `"alt": true` inside an `own` node.
6. "…てもよく", "…てもよい", "may …" as a permission (not a capability) is `P`.
7. "請求項 n に記載の…", "The method of claim n", "The system recited in claim n" is `R`.
8. Not one character changes. If a rule seems to need a reworded leaf, the rule does not apply;
   keep the larger piece as one leaf.

## Examples

Japanese, from `tests/fixtures/src-XX0000001` (made up):

```text
特定の通信規格、特定の記憶形式又は特定の表示形式に依存しない表示部と、
```

```json
{"A": [
  {"N": [{"O": [{"L": "特定の通信規格"}, "、", {"L": "特定の記憶形式"}, "又は", {"L": "特定の表示形式"}]}, "に依存しない"]},
  "表示部と、"], "own": true}
```

The leaf "特定の通信規格" gets "i.e., 特定の通信規格に依存しない"; True means the product does not
depend on it. The `O` is shown as `OR→AND`.

English, from `samples/src-US5946647` claim 1:

```text
a memory storing information including program routines including
an analyzer server for detecting structures in the data, and for linking actions to the detected structures;
a user interface enabling the selection of a detected structure and a linked action; and
an action processor for performing the selected action linked to the selected structure; and
```

```json
{"A": [
  "a memory storing information including program routines including\n",
  {"A": [
    {"A": ["an analyzer server ",
      {"A": [{"L": "for detecting structures in the data"}, ", and ", {"L": "for linking actions to the detected structures"}]},
      ";"], "own": true},
    "\n",
    {"L": "a user interface enabling the selection of a detected structure and a linked action;"}, " and\n",
    {"L": "an action processor for performing the selected action linked to the selected structure;"}
  ]},
  " and"], "own": true}
```

A dependent claim:

```json
{"A": [{"R": 1, "t": "The method of claim 1"}, ", wherein ", {"L": "the moving comprises movement along any desired path."}]}
```

## Workflow

Write the tree for one claim, build, read the first difference, fix, repeat. Labels are assigned by
the build (`1`, `1A`, `1B`, `1B.1`, ...) from the order of nodes; `ai.json` and `tr.<lang>.json`
refer to those labels, so finish the tree before writing them. To see the labels, build once and
export JSON from the page, or read them from the page's tree.
