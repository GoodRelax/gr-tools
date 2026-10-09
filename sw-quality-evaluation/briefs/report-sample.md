# Report sample -- page one (FORMAT ONLY)

> **This is a layout sample for the synthesis agent.** The product, findings, file paths and numbers below are **fictional**. Copy the structure, the order of sections and the kind of content in each part. **Never copy the numbers, the findings or the wording**: every score in a real report comes from `scripts/score_axes.py`, and every sentence from the evidence of that run. A real report is written in OUTPUT_LANGUAGE.

---

# Quality evaluation -- meeting-room booking service (fictional)

| Design score | Can it be used now? | Can it be maintained? |
|---|---|---|
| **6 / 10 Standard** | **With care** | **Easily** |
| Basis: design chart, 66 items -- 39 PASS, 10 MOSTLY, 12 PARTIAL, 5 FAIL -> 79.5% -> 7; one major finding over 12,400 lines (F-001) -> defect level 6; the lower one counts | Basis: no critical finding; the core booking is correct. The major findings occur only under conditions users can notice: use in regions with daylight saving (F-002), simultaneous confirmation (F-001), the first minutes after a cancellation (F-004) | Basis: maintainability 8 (Great); 214 automated tests; no dependency cycles; 4 of 5 change scenarios stay inside one component |

| Product quality: can it be used? | Design and construction: is it well engineered? | Hard spots: are the error-prone parts right? |
|---|---|---|
| ![product](charts/product.svg) | ![design](charts/design.svg) | ![hard spots](charts/hard-spots.svg) |
| The nine characteristics of ISO/IEC 25010:2023. Grey dotted axis = not applicable | Seven design viewpoints; the design score is computed from all their items | Ten places where code most often goes wrong. Dashed axis = cannot judge (not zero) |

## Overall verdict

The design scores 6 (Standard), and the service can be used now with care. Business rules are kept apart from the screens and the database, each component has one clear job, and most names say what they hold, so a newcomer can find where to change things. The core of booking is correct: when two people confirm the same slot at once, the database constraint stops the second booking. Its weaknesses are that booking times are stored in local time and shift by one hour where daylight saving applies (F-002), that the second person in a simultaneous confirmation sees only "internal error" (F-001), and that a cancelled room keeps showing as booked for up to five minutes (F-004); none of these matters in a single time zone without daylight saving, but all must be fixed before offices abroad use it. With 214 tests and clear boundaries, it is easy to maintain. Fixing F-001 and F-002 makes it usable without conditions; treating a failed confirmation as a state of the booking and merging the duplicated date formatting (F-003) would raise the design score to 7 or 8.

## Strengths

1. Business rules do not depend on the screens or the database (`src/booking/` imports nothing from the outer layers; dependency tool: 0 violations).
2. All 23 entry points pass input validation and permission checks through one component (`src/web/guards.py`).
3. Every period is a half-open range, and the names say so (`start`, `end_exclusive`).
4. Money is held as integer minor units, with one rounding rule (`src/billing/money.py`).
5. 214 automated tests guard fees, permissions and the cancellation policy.

## Main risks and their evidence

| Finding | What happens | Where | How it was verified | Found independently by |
|---|---|---|---|---|
| F-001 major | When two people confirm the same slot at once, the second sees only "internal error" and cannot tell what happened (no double booking) | `src/booking/confirm_booking.py:41-58`, `src/web/error_handler.py:22` | Traced: the unique constraint stops the second insert; the failure becomes a generic 500 response. A refuter could not break it | 3 lenses |
| F-002 major | Where daylight saving applies, bookings on the changeover day shift by one hour | `src/booking/slot.py:12`, `src/booking/repository.py:77` | Local time is stored and converted with a fixed offset; recomputed on synthetic dates (the product was not run). Major because the profile includes offices abroad | 2 lenses |
| F-004 major | After a cancellation, the free-room list stays up to five minutes old | `src/rooms/availability_cache.py:15`, `src/booking/cancel_booking.py:30` | The copy is refreshed on confirmation only; cancellation waits for the five-minute expiry | 2 lenses |

## Breakdown

### Product quality

| Characteristic (what it asks) | Importance | Score | What it means here | How computed | Findings |
|---|---|---|---|---|---|
| Reliability (does it hold up when things go wrong?) | high | 6 Standard | Simultaneous confirmation is stopped correctly but reported badly | 21 items: 9 PASS, 4 MOSTLY, 4 PARTIAL, 4 FAIL -> 66.7% -> 6; one major over 12,400 lines -> 6 | F-001, F-004 |
| Functional suitability (does it do what it should?) | high | 6 Standard | 48 of 52 requirements behave as specified; times shift under daylight saving | ... | F-002 |
| Security (does it protect information?) | high | 9 Excellent | Validation and permission checks at every entry point | ... | -- |
| Safety (can it harm people or property?) | -- | Not applicable | No path to physical harm | -- | -- |
| ... one row per characteristic ... | | | | | |

### Design and construction

| Viewpoint (what it asks) | Score | What it means here | How computed | Findings |
|---|---|---|---|---|
| Layers and dependencies (are layers and dependency directions right?) | 10 Outstanding | Business rules depend on nothing outside; no cycles | 9 items: 8 PASS, 1 MOSTLY -> 97.2%, no FAIL -> 10; no findings -> 10 | -- |
| State handling (is state held in one place and robust to event order?) | 6 Standard | One status per booking, but a failed confirmation is not a state | ... | F-001 |
| ... one row per viewpoint ... | | | | |

### Hard spots

| Hard spot (what it asks) | Score | What it means here | How computed | Findings |
|---|---|---|---|---|
| Naming (does every name tell what it denotes?) | 9 Excellent | Names say what they hold; `cnt` and `count` both appear | ... | F-007 |
| Time and dates (clocks, time zones, daylight saving, calendars?) | 3 Poor | Local time stored; one day computed as 86,400 seconds | 8 items: 1 PASS, 1 MOSTLY, 2 PARTIAL, 4 FAIL -> 34.4% -> 3 | F-002, F-005 |
| ... one row per hard spot ... | | | | |

### How scores are computed

(Section 2 of the synthesis brief, in plain words.)

### Scale

| Score | Word (OUTPUT_LANGUAGE) | English | Guide |
|---|---|---|---|
| 10 | (from axes.json) | Outstanding | A model to learn from. No findings |
| ... | | | |
| 1 | (from axes.json) | Unacceptable | The concern is not addressed at all |

### Severity

| Severity | Meaning |
|---|---|
| Minor | No real harm to behaviour or maintenance (inconsistent notation or naming convention) |
| Major | Leads to a defect or to a large maintenance burden |
| Critical | Leads to an outage, data corruption or a security incident, including a main function that silently produces wrong results |

(The sections after page one follow section 5 of the synthesis brief.)
