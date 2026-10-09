# ROB -- error paths, resources, time, input, security, safety

Lens code: `ROB`. Characteristics: `reliability`, `security`, `safety`.

This lens also feeds four of the hard-spot axes of the report: error paths and clean-up (ROB-1 to ROB-7), time and dates (ROB-8), numbers and units (ROB-9), and string boundaries (ROB-10, ROB-11, ROB-13). Judge each of these items on its own.

Error paths and resource release are where code that works in every demo fails in the field: they run only when something goes wrong, so they are rarely exercised. Read them as carefully as the main path.

## Checklist

| Item | Check |
|---|---|
| ROB-1 | **Every failure of an external operation is handled**: file, network, database, device, process and parse operations; the result or error of each is checked |
| ROB-2 | **No swallowed errors**: no empty handlers, no ignored return codes, no catch-all that logs and continues as if nothing happened, unless the reason is stated |
| ROB-3 | **Errors carry context inside, and leak nothing outside**: internal errors say what failed with which input; messages to users or external callers do not expose stack traces, queries, paths or secrets |
| ROB-4 | **Partial failure leaves consistent state**: a multi-step operation that fails half-way rolls back or is resumable; no half-written file or record is left looking valid |
| ROB-5 | **Retries are bounded and safe**: limited count with back-off; the retried operation is idempotent or de-duplicated |
| ROB-6 | **Resources are released on every path**, including error paths, by the language's scoped mechanism where it has one (connections, files, sockets, locks, memory, handles); acquisition and release are paired in the same scope |
| ROB-7 | **Registrations are undone**: listeners, subscriptions, timers and callbacks registered by an object are removed when it ends |
| ROB-8 | **Time**: elapsed time is measured with a monotonic clock, not wall-clock time; stored and exchanged timestamps are in UTC or carry an offset; local time is for display only; date arithmetic uses calendar functions, not fixed seconds per day |
| ROB-9 | **Numbers**: no unchecked overflow, division by zero, or equality comparison of floating-point values; unit conversions are explicit |
| ROB-10 | **External input is validated at the trust boundary**: type, range, length, format, encoding; nothing from outside reaches a query, command, path, template, deserialiser or memory operation unchecked |
| ROB-11 | **Security weaknesses**: injection (query, command, path traversal, template), unsafe deserialisation, hard-coded secrets, missing authentication or authorisation checks on a privileged operation, weak or misused cryptography, sensitive data written to logs. Use `REPORT_DIR/tools/secrets.*` and `tools/lint-*` outputs |
| ROB-12 | **Fail-safe behaviour** (only if the profile's harm class includes physical harm, data loss or loss of a critical service; otherwise `NA`): on an internal fault the system moves to a defined safe state; hazards are detected and signalled; watchdogs or time-outs guard every wait that could block forever |
| ROB-13 | **String boundaries**: wherever text crosses into another language or format -- HTML, SQL, shell, regular expressions, JSON, CSV, URLs, file paths, log lines -- it is encoded for that target (escaping, parameter binding, quoting) and decoded on the way back (entities, percent-encoding); character encodings are explicit at every input and output; nothing is built by concatenating untrusted text into code or markup |

## Method

1. List the external operations in your region (from `map.md` and by search) and trace each one's failure path to where it ends.
2. List resource acquisitions and find the matching release on each path, including early returns and exceptions.
3. Trace each entry point that receives external input to its first validation.
4. Use tool outputs for security patterns, then confirm each hit by reading -- a tool hit is not a finding until you have read it.

Severity guide: by the profile's harm class. An unchecked external input reaching a dangerous operation -> `critical` or `major`; a swallowed error on a data path -> `major`; a leak in a long-running process -> `major`, in a short-lived tool -> `minor`.
