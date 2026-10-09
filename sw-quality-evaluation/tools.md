# Static tools -- open source only

The coordinator checks which of these are present and asks the user before installing any missing one.
Commercial tools are out of scope.

**Rules for every tool run**

- Run on CODE_DIR read-only. Never use a mode that rewrites files (`--fix`, `--write`, `--write-changes`, formatters).
- Never use a tool that has to **build the project or install its dependencies** to work: that executes the project's own build scripts and install hooks. Such tools are listed at the end as excluded.
- **Run every tool with its working directory inside `REPORT_DIR/tools/`**, and give output paths explicitly. Many tools write a default output or cache file (`report/`, `.eslintcache`, `.cache/`) into the working directory -- that must never be CODE_DIR. Do not pass flags that create caches.
- Tools that read a configuration file from the scanned tree (`.eslintrc`, `pyproject.toml`) must be pointed at a configuration of your own in REPORT_DIR, so the project's configuration -- which may load project plugins -- is not used.
- Save raw output under `REPORT_DIR/tools/` and record tool, version, command and exit status in `tools/index.md`.
- Prefer ephemeral runners (`pipx run <pkg>`, `npx --yes <pkg>`) over global installs.
- Tool hits are leads, not findings. An agent reads the code before reporting anything a tool flagged.

> The names, package names and capabilities below are from the author's knowledge at the time of writing and were not re-verified. Confirm the licence, the current version and the install method on each project's own page before installing.

## Language-independent

| Purpose | Tool | Package / source | Notes |
|---|---|---|---|
| Size per file and language | scc | release binary | Fast; also gives a rough complexity count |
| Size per file and language | cloc | release, or npm `cloc` | Alternative to scc |
| Function length and cyclomatic complexity | lizard | PyPI `lizard` | Many languages from source alone; CSV / XML output |
| Copy-paste clones | jscpd | npm `jscpd` | Many languages; set a minimum token count, report JSON |
| Copy-paste clones | PMD CPD | PMD distribution (needs Java) | Alternative to jscpd |
| Spelling, including inside identifiers | typos | release binary, or cargo `typos-cli` | Splits camelCase and snake_case; never run with its write mode |
| Spelling | codespell | PyPI `codespell` | Alternative; weaker at splitting identifiers |
| Committed secrets | gitleaks | release binary | Use its directory-scan mode (not git history) unless the user asks for history |
| Identifier inventory | Universal Ctags | release binary | Kinds, scopes and line numbers for every declaration; feeds `identifiers.txt` |
| Structural search | ast-grep | npm `@ast-grep/cli`, or PyPI `ast-grep-cli` | Syntax-aware search patterns across many languages |
| Text search | ripgrep | release binary | Usually already present with Claude Code |
| Pattern-based bug and security scan | Semgrep (community edition) | PyPI `semgrep` | Rule packs are downloaded from the network -- ask the user first; run with metrics off; native Windows support has been limited, so it may need WSL |

## Language-specific (work from source, without the project's dependencies)

| Language | Tool | Package / source | Purpose |
|---|---|---|---|
| C / C++ | Cppcheck | release / package manager | Bugs: bounds, leaks, null, undefined behaviour |
| C / C++ | Flawfinder | PyPI `flawfinder` | Risky function use (security) |
| C / C++ | clang-tidy | LLVM | **Only if a `compile_commands.json` already exists in CODE_DIR.** Generating one runs the build configuration -- do not |
| Python | Ruff | PyPI `ruff` | Lint (check mode only) |
| Python | Radon | PyPI `radon` | Complexity, maintainability index |
| Python | Vulture | PyPI `vulture` | Dead code |
| Python | Bandit | PyPI `bandit` | Security patterns |
| JavaScript / TypeScript | madge | npm `madge` | Module dependency graph and cycles |
| JavaScript / TypeScript | dependency-cruiser | npm `dependency-cruiser` | Dependency rules and cycles |
| Java | PMD | PMD distribution (needs Java) | Source-level rules |
| Java | Checkstyle | release jar (needs Java) | Naming and convention consistency |
| Kotlin | detekt | release jar / CLI | Source-level rules |
| Swift | SwiftLint | release binary | Source-level rules |
| Ruby | RuboCop | gem `rubocop` | Lint (no auto-correct) |
| Shell | ShellCheck | release binary | Shell script defects |

## Excluded -- they build the project or need its dependencies

| Tool kind | Why excluded |
|---|---|
| Analyzers that run on compiled output (bytecode or binary analyzers) | Need a build |
| Compiler-integrated linters that compile the crate, module or project | Run build scripts; need dependencies |
| Type checkers that resolve third-party types | Need dependencies installed |
| Linters whose project configuration loads plugins from the project's dependencies | Need dependencies installed. A linter may still be run with a minimal configuration of its own, written into REPORT_DIR |
| Test runners and coverage tools | Execute the code |
