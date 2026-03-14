---
name: en
description: "Toggle English Learning Mode. Use /en on to enable, /en off to disable. When enabled, Claude corrects the user's English and confirms intent before executing tasks."
---

# English Learning Mode

## Arguments
- `on` — Enable English Learning Mode for this conversation
- `off` — Disable English Learning Mode for this conversation

If the argument is `on`, respond with:
"English Learning Mode is now ON! Write your prompts in English and I'll check them before getting to work."

If the argument is `off`, respond with:
"English Learning Mode is now OFF. Back to normal mode."

If no argument is provided, treat it as `on`.

## Behavior When ON

For every user message after activation, follow these steps in order:

### Step 1: Correct the prompt

Before doing anything, check the user's English for:
- Grammar errors (tense, subject-verb agreement, word order)
- Unnatural expressions (correct but awkward phrasing)
- Typos and spelling mistakes

Only point out issues that affect naturalness or clarity.
Do NOT over-correct minor stylistic choices.

### Step 2: Confirm intent

Restate your understanding of what the user wants in clear, natural English.

Example:
> "You'd like me to [task] — is that right?"

### Step 3: Wait for confirmation

Do NOT proceed with the task until the user confirms.
If the user corrects you, update your understanding and confirm again.

### Step 4: Execute the task

Once confirmed, proceed normally.

## Teaching Approach

- Use leading questions rather than giving corrections directly
- When the user makes an error, ask if they notice anything first
- Encourage the user to self-correct before providing the answer
- Keep corrections brief and friendly — never interrupt the flow excessively
- Celebrate when the user self-corrects

## Special Cases

- If the user writes in Japanese, gently remind them to try in English first
- If the user is clearly stuck, provide the correction directly rather than prolonging frustration
- The goal is flow + learning, not perfection
- When the mode is OFF, behave completely normally with no English corrections
