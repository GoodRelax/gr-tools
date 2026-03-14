``````markdown
# Claude Ecosystem Diagnostic Batch File Specification

> Version: 1.2
> Last updated: 2026-03-14

---

## 1. Purpose and Policy

This tool performs **read-only** diagnostics of the Claude ecosystem (Desktop / CLI / VS Code Extension / configuration files) on Windows, and highlights gaps from the recommended configuration.

Design principles:
- **Read-Only**: No settings are changed and no files are written (except output files)
- **No admin privileges required**: All checks run under standard user permissions (see Section 7.3 for details)
- **Two outputs**: A human-readable summary + a structured log for Claude
- **Claude integration**: Pass the log to Claude to receive improvement suggestions and enable semi-automated reconfiguration

---

## 2. Overall Flow

**Diagnostic flow:**

```mermaid
flowchart TB
    Start["User runs<br/>diagnose-claude.bat"]
    Check1["C1: Desktop installation check"]
    Check2["C2: CLI installation check"]
    Check3["C3: VS Code extension check"]
    Check4["C4: Credentials check"]
    Check5["C5: Global settings.json check"]
    Check6["C6: Project settings.json check"]
    Check7["C7: Desktop config check"]
    Check8["C8: PATH environment variable check"]
    Check9["C9: claude.exe full scan"]
    Check10["C10: Proxy environment variable check"]
    Check11["C11: MCP config file check"]
    Summary["Generate human-readable summary<br/>diagnosis-summary.txt"]
    Log["Generate Claude log<br/>diagnosis-for-claude.json"]
    Display["Display summary on screen"]
    Prompt["Show Claude integration guide"]
    Action1["A1: Ask whether to display<br/>proxy setting values on screen"]
    Action2["A2: Ask whether to open<br/>MCP config folder in Explorer"]
    Done["End"]

    Start -->|"Start"| Check1
    Check1 -->|"Next"| Check2
    Check2 -->|"Next"| Check3
    Check3 -->|"Next"| Check4
    Check4 -->|"Next"| Check5
    Check5 -->|"Next"| Check6
    Check6 -->|"Next"| Check7
    Check7 -->|"Next"| Check8
    Check8 -->|"Next"| Check9
    Check9 -->|"Next"| Check10
    Check10 -->|"Next"| Check11
    Check11 -->|"Aggregate"| Summary
    Check11 -->|"Aggregate"| Log
    Summary -->|"Display"| Display
    Log -->|"Guide"| Prompt
    Prompt -->|"Interactive"| Action1
    Action1 -->|"Next"| Action2
    Action2 -->|"Complete"| Done
```

The batch file runs 11 checks in sequence, generates a summary and log, and then offers interactive actions (A1: display proxy values, A2: open MCP folder in Explorer) one by one.

---

## 3. File Structure

**Input/output file structure:**

```text
gr-tools/
└── gr-claude-toolkit/
    ├── README.md                        ... Tool list and usage
    └── diagnose/
        ├── diagnose-claude.bat          ... Diagnostic batch file
        ├── Claude_Diagnostic_Spec-ja.md ... This specification (Japanese)
        ├── Claude_Diagnostic_Spec-en.md ... This specification (English)
        ├── [output] diagnosis-summary.txt ... Human-readable summary (generated at runtime)
        └── [output] diagnosis-for-claude.json ... Structured log for Claude (generated at runtime)
```

Output files are written to the same folder as the batch file (`diagnose/`). Existing files are overwritten (diagnostic results should always reflect the latest state).

---

## 4. Diagnostic Item Details

### C1: Desktop Installation Check

| Item | Details |
|---|---|
| Target | Existence of MSIX package `Claude` |
| Method | `powershell -Command "Get-AppxPackage *Claude*"` |
| Collected info | PackageFamilyName, Version, InstallLocation, Publisher |
| Pass criteria | Package exists. Publisher is `Anthropic, PBC` |
| Warning condition | Multiple versions exist (possible leftover old version) |

### C2: CLI Installation Check

| Item | Details |
|---|---|
| Target | Existence and version of the `claude` command |
| Method | `where claude` + `claude --version` |
| Collected info | Executable path, version number |
| Pass criteria | `claude` exists on PATH and version can be retrieved |
| Warning condition | `where claude` returns multiple paths (duplicate installation) |
| Additional check | Desktop Agent Mode binary: list version folders under `%APPDATA%\Claude\claude-code\` |
| Warning condition | Old versions of `claude.exe` remain for Agent Mode (disk waste; each is approx. 239MB) |

Desktop downloads CLI binaries independently to `%APPDATA%\Claude\claude-code\{version}\claude.exe` for Agent Mode / Cowork. These are separate copies from the npm CLI and are managed automatically by Desktop. A warning is shown if old versions remain, as they waste disk space.

### C3: VS Code Extension Check

| Item | Details |
|---|---|
| Target | Installation status of the Claude Code extension |
| Method | Search for `anthropic.claude-code` in `code --list-extensions` output |
| Collected info | Extension ID, installation status |
| Pass criteria | `anthropic.claude-code` appears in the list |
| Warning condition | If VS Code itself is not on PATH, SKIP (not an error) |
| Additional check | Extension embedded binary: existence and version of `%USERPROFILE%\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe` |
| Additional check | Version mismatch detection (version difference between npm CLI and VS Code embedded binary) |

The VS Code extension includes its own `claude.exe` binary (approx. 239MB), separate from the npm CLI. Old version folders may remain after extension updates.

### C4: Credentials Check

| Item | Details |
|---|---|
| Target | Existence of `%USERPROFILE%\.claude\.credentials.json` |
| Method | File existence check (`if exist`) |
| Collected info | File existence, file size, last modified date |
| Pass criteria | File exists and size is greater than 0 |
| Note | **Never read or output file contents** (contains authentication tokens) |

### C5: Global settings.json Check

| Item | Details |
|---|---|
| Target | `%USERPROFILE%\.claude\settings.json` |
| Method | File existence check + read contents |
| Collected info | Number of allow entries, deny entries, additionalDirectories, full entry list |
| Pass criteria | File exists |
| Warning condition | 15 or more allow entries (sign of bloat) |
| Warning condition | One-shot command patterns detected (Bash entries containing `mkdir`, `cp`, `mv`, `rm`, `touch`) |
| Warning condition | Project-specific path entries detected (e.g., `Read(//c/...` or domain-specific `WebFetch`) |

### C6: Project settings.json Check

| Item | Details |
|---|---|
| Target | `.claude/settings.json` inside known project folders |
| Scan scope | Current directory when the batch runs, and major development folders directly under `%USERPROFILE%` |
| Method | Folder traversal + file existence check + read contents |
| Collected info | List of detected project settings.json paths, allow entry count for each file |
| Pass criteria | Information gathering only (not an error if none exist) |

### C7: Desktop Config Check

| Item | Details |
|---|---|
| Target | `%APPDATA%\Claude\claude_desktop_config.json` |
| Method | File existence check + read contents |
| Collected info | File existence, number of MCP server definitions, server names |
| Pass criteria | File exists (absence is normal if MCP is not used) |

### C8: PATH Environment Variable Check

| Item | Details |
|---|---|
| Target | Whether npm global path and Node.js path are included in PATH |
| Method | Parse `echo %PATH%` and extract paths containing `npm` / `nodejs` / `node` |
| Collected info | npm global path, Node.js path, existence check for each path |
| Pass criteria | `%APPDATA%\npm` is included in PATH |
| Warning condition | Node.js is not in PATH |

### C9: claude.exe Full Scan

| Item | Details |
|---|---|
| Target | All `claude.exe` files under the user profile |
| Method | `powershell -Command "Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter 'claude.exe' -ErrorAction SilentlyContinue"` |
| Collected info | Full path, file size, last modified date for each binary |
| Pass criteria | Information gathering (existence itself is not an error) |
| Classification rule | Each detected binary is automatically classified into categories below |

**Locations where claude.exe may exist and their classification:**

```mermaid
flowchart TB
    Scan["C9: claude.exe full scan<br/>Recursive search under USERPROFILE"]

    subgraph Expected["Expected locations (3 places)"]
        E1["AppData Roaming npm<br/>claude.exe in node_modules<br/>npm CLI main binary"]
        E2["AppData Roaming Claude<br/>claude.exe in claude-code<br/>Desktop Agent Mode binary"]
        E3[".vscode extensions<br/>claude.exe in native-binary<br/>VS Code extension embedded"]
    end

    subgraph Unexpected["Unexpected locations"]
        U1["claude.exe at paths<br/>other than the above<br/>Possible manual copy or old installer remnant"]
    end

    Scan -->|"Path match"| E1
    Scan -->|"Path match"| E2
    Scan -->|"Path match"| E3
    Scan -->|"Path mismatch"| U1
```

Each binary is automatically classified based on its detected path. A WARNING is issued if a binary is found outside the 3 expected locations.

**Classification rules (partial path matching):**

| Path contains | Category | Description |
|---|---|---|
| `AppData\Roaming\npm` | npm_cli | CLI installed via npm |
| `AppData\Roaming\Claude\claude-code` | desktop_agent | Binary downloaded by Desktop for Agent Mode |
| `.vscode\extensions\anthropic.claude-code` | vscode_extension | Binary embedded in VS Code extension |
| None of the above | unknown | Unexpected location (WARNING) |

**Detecting leftover old versions:**

In the `desktop_agent` category, multiple version folders may exist under `%APPDATA%\Claude\claude-code\`. Similarly, in the `vscode_extension` category, old extension version folders may remain under `.vscode\extensions\`. If binaries other than the latest version exist, a WARNING is issued for "old version remaining".

| State | Judgment | Example |
|---|---|---|
| Only one binary per category | OK | Normal |
| Multiple versions in the same category | WARNING | Both `claude-code\2.1.74\` and `claude-code\2.1.76\` exist |
| Binary in unknown category | WARNING | Possible manual copy or old installer remnant |

**Note:** The MSIX Desktop application itself (`C:\Program Files\WindowsApps\`) is outside the user profile, so it is not included in this scan. Desktop existence is confirmed by `Get-AppxPackage` in C1.

### C10: Proxy Environment Variable Check

| Item | Details |
|---|---|
| Target | Proxy-related environment variables |
| Target variables | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` (and lowercase versions `http_proxy`, `https_proxy`, `no_proxy`) |
| Method | Existence check: batch `if defined`. Format validation: completed entirely within PowerShell |
| Collected info | Whether each variable is set (SET / NOT_SET), format validity (valid / invalid) |
| Pass criteria | Not set = OK (environment without proxy). Set and valid format = OK |
| Warning condition | Set but invalid format (does not contain `://`, host part is empty, etc.) |
| Warning condition | Only one of the uppercase or lowercase version is set (different tools reference different variables) |

**Format validation rules:**

| Pattern | Judgment | Example |
|---|---|---|
| Contains `://` and host part is not empty | valid | `http://proxy.example.com:8080` |
| Hostname only (no `://`) with port | valid | `proxy.example.com:8080` |
| Empty string or whitespace only | invalid | `""`, `" "` |
| Other (cannot determine) | unknown | Recorded as-is since individual judgment is not possible |

**Important security constraint:**

Proxy URLs may contain credentials (`http://user:password@proxy:port`). **Proxy environment variable values must never be output.**

| Operation | Safety | Reason |
|---|---|---|
| `if defined HTTP_PROXY` | **Safe** | Does not expand the value |
| Validate within PowerShell and return only `true`/`false` | **Safe** | Value does not enter batch variables |
| `echo %HTTP_PROXY%` | **Dangerous** | Value leaks to console and log |
| `set "VAR=%HTTP_PROXY%"` | **Dangerous** | Value is stored in batch variable |

**Implementation approach:** Format validation is completed entirely within PowerShell, and only `true`/`false` is output.

```batch
REM Safe: value never leaves PowerShell process
for /f "tokens=*" %%a in ('powershell -NoProfile -Command ^
  "$v=$env:HTTP_PROXY; if($v -and $v -match '://\S+'){echo 'true'}else{echo 'false'}"') do (
    set "C10_HTTP_FORMAT_VALID=%%a"
)
```

### C11: MCP Config File Check

| Item | Details |
|---|---|
| Target | Existence and placement of config files containing MCP server definitions |
| Scan scope | The 3 locations listed below |
| Collected info | Whether each file exists, MCP server name list, whether a Jira server is present |
| Pass criteria | Information gathering is the main purpose (not an error if MCP is not used) |
| Warning condition | Jira server exists in Desktop config but not in CLI config (or vice versa) |

**Files to scan:**

| Location | File path | Purpose |
|---|---|---|
| Desktop config | `%APPDATA%\Claude\claude_desktop_config.json` | MCP settings for Desktop app (same file as C7) |
| Global MCP | `%USERPROFILE%\.claude\mcp.json` | Claude CLI global MCP settings |
| Project MCP | `.mcp.json` directly under each project | Project-specific MCP settings (same scan directories as C6) |

**Relationship with C7:** C7 checks the existence and overview (MCP server count) of the Desktop config file. C11 performs a cross-cutting check of MCP settings and verifies consistency across Desktop, CLI, and project configurations. In particular, it confirms that MCP servers like Jira integration (which differ by company) are placed in the correct locations.

**How to retrieve MCP server names:**

```batch
REM Extract server names from JSON using PowerShell
REM Only output server names, NEVER output env block contents (may contain API tokens)
for /f "tokens=*" %%a in ('powershell -NoProfile -Command ^
  "$j=Get-Content '%APPDATA%\Claude\claude_desktop_config.json' -Raw 2>$null | ConvertFrom-Json; ^
   if($j.mcpServers){$j.mcpServers.PSObject.Properties.Name -join ','}"') do (
    set "C11_DESKTOP_SERVERS=%%a"
)
```

**Security notes:**

| Item | Policy |
|---|---|
| MCP server `env` block | **Do not output** (may contain secrets such as API tokens) |
| MCP server `command` / `args` | OK to output (execution command path info is useful for diagnostics) |
| Server names | OK to output |

**Jira detection rule:** Any server whose name contains `jira` (case-insensitive) is treated as a Jira server.

---

### Interactive Actions (After Diagnostic Completion)

After outputting diagnostic results, the following actions are offered in order. Each is executed only if the user enters `yes`. **Action results are not written to files (screen display only).**

#### A1: Display Proxy Environment Variable Values on Screen

| Item | Details |
|---|---|
| Purpose | Visual confirmation of proxy settings (safe method that does not persist values to file) |
| Target variables | `HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY` (and lowercase versions) |
| Display method | Display environment variable values as-is on screen (no masking) |
| File output | **None** (screen display only; nothing is written to diagnosis-summary.txt or diagnosis-for-claude.json) |
| If not set | Display `(not set)` |

**Screen display example:**

```text
[A1] Show proxy environment variable values on screen? (yes/no): yes

  HTTP_PROXY  = http://proxy.company.com:8080
  HTTPS_PROXY = http://proxy.company.com:8080
  NO_PROXY    = localhost,127.0.0.1,.company.com
  http_proxy  = (not set)
  https_proxy = (not set)
  no_proxy    = (not set)
```

**Security note:** Values displayed in A1 are never written to any file. This is clearly separated from the C10 diagnostic results (which only contain SET/NOT_SET and format validity). Screen display is volatile and intended solely for visual confirmation by the user.

#### A2: Open MCP Config File Folder in Explorer

| Item | Details |
|---|---|
| Purpose | Quick access to MCP config file editing locations |
| Target | Folders containing MCP config files detected in C11 |
| Behavior | Display a numbered list; user enters a number to open that folder in Explorer |
| Loop | Repeatable until user enters 0 (allows opening multiple folders in sequence) |
| If no folders found | Display `No MCP config locations found.` and skip |

**Screen display example:**

```text
[A2] Open MCP config folder in Explorer? (yes/no): yes

  Available MCP config locations:
    1. Desktop config: C:\Users\good_\AppData\Roaming\Claude
    2. Project MCP: C:\Users\good_\...\claude-code-full-auto-dev
    0. Exit

  Enter number (0 to exit): 1
  Opening: C:\Users\good_\AppData\Roaming\Claude

  Enter number (0 to exit): 2
  Opening: C:\Users\good_\...\claude-code-full-auto-dev

  Enter number (0 to exit): 0
  Done.
```

**Design intent:** MCP settings are spread across multiple locations (Desktop config / Global / Project). A2 allows the user to view diagnostic results and immediately open the relevant folder to edit config files. The loop mechanism allows opening multiple folders in succession.

---

## 5. Output Format

### 5.1 Human-Readable Summary (diagnosis-summary.txt)

**Summary output example:**

```text
=============================================================
  Claude Ecosystem Diagnostic Report
  Generated: 2026-03-14 15:30:45
=============================================================

[C1] Desktop Installation
  Status  : OK
  Version : 1.6.6679.0
  Package : AnthropicPBC.Claude_1.6.6679.0_neutral__pzs8sxrjxfjjc
  Publisher: CN=Anthropic, PBC

[C2] CLI Installation
  Status  : OK
  Version : 2.1.76
  Path    : C:\Users\good_\AppData\Roaming\npm\claude.cmd

[C3] VS Code Extension
  Status  : OK
  Extension: anthropic.claude-code

[C4] Credentials
  Status  : OK
  File    : EXISTS (last modified: 2026-03-14)
  Note    : Content not inspected (security)

[C5] Global settings.json
  Status  : WARNING
  Path    : C:\Users\good_\.claude\settings.json
  Allow entries    : 47
  Deny entries     : 0
  Additional dirs  : 2
  Warnings:
    - 47 allow entries detected (recommended: <15)
    - One-shot commands found: Bash(mkdir -p ...), Bash(rm ...)
    - Project-specific entries found: Read(//c/.../articles/**)

[C6] Project settings.json
  Found 3 project settings:
    - C:\Users\good_\...\articles\.claude\settings.json (12 entries)
    - C:\Users\good_\...\gr-simple-md-renderer\.claude\settings.json (3 entries)
    - C:\Users\good_\...\claude-code-full-auto-dev\.claude\settings.json (1 entry)

[C7] Desktop Config
  Status  : OK
  Path    : C:\Users\good_\AppData\Roaming\Claude\claude_desktop_config.json
  MCP servers: 0

[C8] PATH Check
  Status  : OK
  npm global: C:\Users\good_\AppData\Roaming\npm (EXISTS in PATH)
  Node.js   : C:\Program Files\nodejs (EXISTS in PATH)

[C9] claude.exe Binary Scan
  Status  : WARNING
  Found 3 binaries:
    [npm_cli]          AppData\Roaming\npm\node_modules\...\claude.exe (239MB, v2.1.76)
    [desktop_agent]    AppData\Roaming\Claude\claude-code\2.1.74\claude.exe (239MB, OLD)
    [vscode_extension] .vscode\extensions\...-2.1.75-...\claude.exe (239MB, v2.1.75)
  Warnings:
    - Old desktop_agent binary: 2.1.74 (latest: 2.1.76) - 239MB reclaimable

[C10] Proxy Settings
  Status    : OK
  HTTP_PROXY : SET [format: valid]
  HTTPS_PROXY: SET [format: valid]
  NO_PROXY   : SET
  Note      : Actual values not shown [security]

[C11] MCP Config Files
  Status  : OK
  Desktop config: EXISTS [2 servers: filesystem, jira]
  Global MCP    : NOT FOUND
  Project MCP   :
    - C:\Users\good_\...\my-project\.mcp.json [1 server: jira]
  Jira servers found: 2 locations

=============================================================
  Summary: 8 OK / 2 WARNING / 0 ERROR / 1 INFO
  Log for Claude: diagnosis-for-claude.json
=============================================================
```

The same content is used for both screen display and file output. It uses ASCII only to prevent character encoding issues.

### 5.2 Structured Log for Claude (diagnosis-for-claude.json)

**Log output schema:**

```json
{
  "format_version": "1.0",
  "generated_at": "2026-03-14T15:30:45+09:00",
  "machine_name": "NAMA_CHAN",
  "username": "good_",
  "diagnostics": {
    "C1_desktop": {
      "status": "OK",
      "version": "1.6.6679.0",
      "package_family": "AnthropicPBC.Claude_pzs8sxrjxfjjc",
      "install_location": "C:\\Program Files\\WindowsApps\\AnthropicPBC.Claude_1.6.6679.0_neutral__pzs8sxrjxfjjc",
      "warnings": []
    },
    "C2_cli": {
      "status": "OK",
      "version": "2.1.76",
      "path": "C:\\Users\\good_\\AppData\\Roaming\\npm\\claude.cmd",
      "duplicate_paths": [],
      "warnings": []
    },
    "C3_vscode_extension": {
      "status": "OK",
      "extension_id": "anthropic.claude-code",
      "warnings": []
    },
    "C4_credentials": {
      "status": "OK",
      "file_exists": true,
      "file_size_bytes": 1234,
      "last_modified": "2026-03-14",
      "warnings": []
    },
    "C5_global_settings": {
      "status": "WARNING",
      "path": "C:\\Users\\good_\\.claude\\settings.json",
      "allow_count": 47,
      "deny_count": 0,
      "additional_dirs_count": 2,
      "allow_entries": [
        "Bash(pnpm test:*)",
        "Bash(cmd /c \"pnpm test\")",
        "WebSearch"
      ],
      "additional_directories": [
        "C:\\Users\\good_\\AppData\\Local\\Temp",
        "C:\\Users\\good_\\OneDrive\\Documents\\GitHub\\articles\\ai-native-spec"
      ],
      "warnings": [
        "allow_count_high: 47 entries (threshold: 15)",
        "oneshot_commands_detected: Bash(mkdir -p ...), Bash(rm ...)",
        "project_specific_entries_detected: Read(//c/.../articles/**)"
      ],
      "raw_content": "{...full JSON content of settings.json...}"
    },
    "C6_project_settings": {
      "status": "OK",
      "projects_found": [
        {
          "path": "C:\\Users\\good_\\...\\articles\\.claude\\settings.json",
          "allow_count": 12,
          "raw_content": "{...}"
        }
      ],
      "warnings": []
    },
    "C7_desktop_config": {
      "status": "OK",
      "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude_desktop_config.json",
      "mcp_server_count": 0,
      "mcp_server_names": [],
      "raw_content": "{...}",
      "warnings": []
    },
    "C8_path": {
      "status": "OK",
      "npm_global_in_path": true,
      "npm_global_path": "C:\\Users\\good_\\AppData\\Roaming\\npm",
      "nodejs_in_path": true,
      "nodejs_path": "C:\\Program Files\\nodejs",
      "warnings": []
    },
    "C9_binary_scan": {
      "status": "WARNING",
      "binaries_found": [
        {
          "path": "C:\\Users\\good_\\AppData\\Roaming\\npm\\node_modules\\@anthropic-ai\\claude-code\\cli\\claude.exe",
          "category": "npm_cli",
          "size_bytes": 239061152,
          "last_modified": "2026-03-14",
          "version_hint": "2.1.76"
        },
        {
          "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude-code\\2.1.74\\claude.exe",
          "category": "desktop_agent",
          "size_bytes": 238872736,
          "last_modified": "2026-03-12",
          "version_hint": "2.1.74"
        },
        {
          "path": "C:\\Users\\good_\\.vscode\\extensions\\anthropic.claude-code-2.1.75-win32-x64\\resources\\native-binary\\claude.exe",
          "category": "vscode_extension",
          "size_bytes": 239061152,
          "last_modified": "2026-03-13",
          "version_hint": "2.1.75"
        }
      ],
      "categories_summary": {
        "npm_cli": 1,
        "desktop_agent": 1,
        "vscode_extension": 1,
        "unknown": 0
      },
      "old_versions_detected": [
        {
          "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude-code\\2.1.74\\claude.exe",
          "category": "desktop_agent",
          "size_bytes": 238872736,
          "reclaimable": true
        }
      ],
      "total_disk_usage_bytes": 717195040,
      "reclaimable_bytes": 238872736,
      "warnings": [
        "old_desktop_agent_binary: 2.1.74 (239MB reclaimable)",
        "version_mismatch: npm=2.1.76, vscode=2.1.75, desktop_agent=2.1.74"
      ]
    },
    "C10_proxy": {
      "status": "OK",
      "http_proxy_set": true,
      "http_proxy_format_valid": true,
      "https_proxy_set": true,
      "https_proxy_format_valid": true,
      "no_proxy_set": true,
      "http_proxy_lowercase_set": true,
      "https_proxy_lowercase_set": true,
      "no_proxy_lowercase_set": true,
      "case_mismatch": false,
      "warnings": []
    },
    "C11_mcp_config": {
      "status": "OK",
      "locations": [
        {
          "type": "desktop_config",
          "path": "C:\\Users\\good_\\AppData\\Roaming\\Claude\\claude_desktop_config.json",
          "exists": true,
          "server_names": ["filesystem", "jira"],
          "has_jira": true
        },
        {
          "type": "global_mcp",
          "path": "C:\\Users\\good_\\.claude\\mcp.json",
          "exists": false,
          "server_names": [],
          "has_jira": false
        },
        {
          "type": "project_mcp",
          "path": "C:\\Users\\good_\\...\\my-project\\.mcp.json",
          "exists": true,
          "server_names": ["jira"],
          "has_jira": true
        }
      ],
      "jira_found_count": 2,
      "warnings": []
    }
  },
  "summary": {
    "ok_count": 8,
    "warning_count": 2,
    "error_count": 0,
    "total_warnings": [
      "C5: allow_count_high (47 entries)",
      "C5: oneshot_commands_detected",
      "C5: project_specific_entries_detected",
      "C9: old_desktop_agent_binary (239MB reclaimable)",
      "C9: version_mismatch across clients"
    ]
  }
}
```

The Claude log includes the full content of config files as `raw_content`. This allows Claude to generate specific improvement suggestions. However, `C4_credentials` never includes file content (for security reasons).

---

## 6. Claude Integration Flow (Semi-Automated Reconfiguration)

**Claude integration flow:**

```mermaid
flowchart TB
    Bat["Run diagnose-claude.bat"]
    JSON["Generate diagnosis-for-claude.json"]
    User["User passes JSON<br/>to Claude"]
    Analyze["Claude analyzes<br/>diagnostic results"]
    Proposal["Claude presents improvement suggestions<br/>including specific JSON diffs"]
    Confirm["User reviews suggestions<br/>Approve or request changes"]
    Backup["Claude creates backup<br/>settings.json.bak.YYYYMMDD-HHMMSS"]
    Apply["Claude applies settings"]
    Recheck["Re-run diagnose-claude.bat<br/>to verify improvements"]

    Bat -->|"Generate"| JSON
    JSON -->|"Copy-paste or specify file"| User
    User -->|"Input"| Analyze
    Analyze -->|"Output"| Proposal
    Proposal -->|"Review"| Confirm
    Confirm -->|"After approval"| Backup
    Backup -->|"After backup"| Apply
    Apply -->|"Verify"| Recheck
```

The cycle of Diagnose -> Analyze -> Suggest -> Approve -> Backup -> Apply -> Re-diagnose allows settings to be improved safely.

### 6.1 Example Prompt for Passing Results to Claude

**Prompt template for Claude:**

```text
Below is the output from the Claude ecosystem diagnostic tool.
Please analyze the diagnostic results and provide improvement suggestions.

Please include the following in your suggestions:
1. Explanation of each warning and recommended action
2. Specific changes to settings.json (before/after diff)
3. Suggested destination for project-specific entries

If you apply settings changes, always create a backup before making changes.
Backup filename: original-filename.bak.YYYYMMDD-HHMMSS

[Paste the contents of diagnosis-for-claude.json here]
```

This template is displayed on screen after batch execution so users can copy and use it.

### 6.2 Backup Rules

| Item | Rule |
|---|---|
| Backup naming | `original-filename.bak.YYYYMMDD-HHMMSS` |
| Example | `settings.json.bak.20260314-153045` |
| Location | Same folder as the original file |
| Timing | Immediately before Claude applies settings changes |
| Retention | Not auto-deleted (user decides when to manually delete) |

### 6.3 Examples of Improvement Actions by Claude

**Improvement action categories:**

```mermaid
flowchart LR
    subgraph Actions["Actions Claude may suggest"]
        A1["Remove one-shot<br/>permissions from global"]
        A2["Move project-specific entries<br/>to project settings"]
        A3["Consolidate<br/>duplicate entries"]
        A4["Add missing<br/>recommended settings"]
        A5["Suggest deleting<br/>old version binaries"]
    end

    subgraph Safety["Safety mechanisms"]
        S1["Pre-change backup"]
        S2["User approval required"]
        S3["Post-change re-diagnosis"]
    end

    A1 -->|"Before execution"| S1
    A2 -->|"Before execution"| S1
    A3 -->|"Before execution"| S1
    A4 -->|"Before execution"| S1
    A5 -->|"Before execution"| S1
    S1 -->|"Confirm"| S2
    S2 -->|"After apply"| S3
```

All actions go through the safety flow of Backup -> Approval -> Apply -> Re-diagnose.

---

## 7. Implementation Constraints and Notes

### 7.1 Technical Constraints

| Constraint | Approach |
|---|---|
| Batch files (.bat) have no JSON parser | Use PowerShell one-liners to parse JSON |
| Character encoding | Output is UTF-8 (`chcp 65001`). Comments in batch file are ASCII only |
| Execution privileges | No admin privileges required. All checks run under user permissions |
| PowerShell execution policy | Use `-ExecutionPolicy Bypass` to bypass individual script restrictions |

### 7.2 Security Notes

| Item | Policy |
|---|---|
| `.credentials.json` | Existence check only. Content is never read or output |
| OAuth tokens | `config.json`'s `oauth:tokenCache` is not output |
| Environment variable secrets | Only PATH is retrieved. No other environment variables are collected |
| Proxy environment variables | Values are never output (to prevent `user:password@proxy` leakage). Only SET/NOT_SET and format validity are output. Format validation is completed entirely within PowerShell; values are never stored in batch variables |
| MCP server env | Only server names are retrieved. Tokens in `env` blocks are not output |

### 7.3 Why Admin Privileges Are Not Required

Claude components may also be installed under `C:\Program Files\`, but all operations needed for diagnostics can run under standard user permissions.

**Permission requirements for each check:**

| Check | Target location | Access method | Admin required |
|---|---|---|---|
| C1: Desktop | `C:\Program Files\WindowsApps\` | `Get-AppxPackage` (reads from package DB; no direct folder access needed) | **No** |
| C2: CLI | `%APPDATA%\npm\` (under user profile) | `where claude` + `claude --version` | **No** |
| C3: VS Code | `%USERPROFILE%\.vscode\` (under user profile) | `code --list-extensions` | **No** |
| C4: Credentials | `%USERPROFILE%\.claude\` (under user profile) | File existence check | **No** |
| C5-C6: settings.json | `%USERPROFILE%\.claude\` (under user profile) | File read | **No** |
| C7: Desktop config | `%APPDATA%\Claude\` (under user profile) | File read | **No** |
| C8: PATH | Environment variable | `echo %PATH%` | **No** |
| C9: Binary scan | Recursive search under `%USERPROFILE%` | `Get-ChildItem -Recurse` | **No** |
| C10: Proxy | Environment variables | `if defined` + validation within PowerShell | **No** |
| C11: MCP config | `%APPDATA%\Claude\`, `%USERPROFILE%\.claude\`, under projects | File read | **No** |

**Important design decisions:**

- The MSIX `InstallLocation` (`C:\Program Files\WindowsApps\...`) may not be directly accessible without admin privileges. However, the `Get-AppxPackage` command retrieves metadata (version, path, Publisher) from the package database, so direct folder access is not needed
- Node.js itself is in `C:\Program Files\nodejs\`, but read-only access is possible under user permissions. The diagnostic only retrieves the version via `node -v` and does not read files within the folder
- The C9 binary scan is limited to `%USERPROFILE%`. The Desktop application in `C:\Program Files\WindowsApps\` is already detected by `Get-AppxPackage` in C1, so it is excluded from the scan

### 7.4 Error Handling

| Situation | Behavior |
|---|---|
| File does not exist | Set status to `MISSING` and continue (no error stop) |
| PowerShell command fails | Set status to `ERROR`, record error message, and continue |
| JSON parse error | Set status to `PARSE_ERROR`, record raw text as-is, and continue |
| VS Code is not installed | Set status to `SKIP` and continue (not a required component) |

---

## 8. Batch File Screen Output Example

**Screen display during execution:**

```text
=============================================================
  Claude Ecosystem Diagnostic Tool v1.0
=============================================================

Checking [C1] Desktop Installation...    OK (v1.1.6679.0)
Checking [C2] CLI Installation...        OK (v2.1.76)
Checking [C3] VS Code Extension...       OK (v2.1.75, embedded binary: v2.1.75)
Checking [C4] Credentials...             OK
Checking [C5] Global settings.json...    WARNING (47 allow entries)
Checking [C6] Project settings.json...   OK (3 projects found)
Checking [C7] Desktop Config...          OK
Checking [C8] PATH Check...              OK
Checking [C9] Binary Scan...             WARNING (old version: 239MB reclaimable)
Checking [C10] Proxy Settings...         OK
Checking [C11] MCP Config Files...       OK [Jira: 2 locations]

=============================================================
  Result: 9 OK / 2 WARNING / 0 ERROR
=============================================================

Output files:
  Summary : C:\Users\good_\diagnosis-summary.txt
  Log     : C:\Users\good_\diagnosis-for-claude.json

-------------------------------------------------------------
To get improvement suggestions from Claude, copy the prompt
below and paste it into Claude along with the log file:
-------------------------------------------------------------

  [Prompt template displayed here]

=============================================================
  Optional Actions (screen-only, not saved to files)
=============================================================

[A1] Show proxy environment variable values on screen? (yes/no): yes

  HTTP_PROXY  = http://proxy.company.com:8080
  HTTPS_PROXY = http://proxy.company.com:8080
  NO_PROXY    = localhost,127.0.0.1,.company.com
  http_proxy  = (not set)
  https_proxy = (not set)
  no_proxy    = (not set)

[A2] Open MCP config folder in Explorer? (yes/no): yes

  Available MCP config locations:
    1. Desktop config: C:\Users\good_\AppData\Roaming\Claude
    2. Project MCP: C:\Users\good_\...\claude-code-full-auto-dev
    0. Exit

  Enter number (0 to exit): 1
  Opening: C:\Users\good_\AppData\Roaming\Claude

  Enter number (0 to exit): 0
  Done.

=============================================================
  Done. Press any key to exit.
=============================================================
```

Each check item is displayed in real time, one line at a time, with the status shown at the right end. After displaying file paths and the Claude integration prompt template, interactive actions (A1: display proxy values, A2: open MCP folder in Explorer) are offered in order. Interactive action results are not written to files (screen display only).
``````
