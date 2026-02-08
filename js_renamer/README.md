# JavaScript Renamer v3.1 (Alpha)

> **[ALPHA VERSION WARNING]**
> This software is currently in the **Alpha** stage. It may contain bugs or incomplete features.
> **ALWAYS backup your original HTML/JS files before using this tool.**
> Use at your own risk.
> A safe, AST-based tool for renaming JavaScript identifiers (variables, functions, classes, parameters) embedded within HTML files.

Unlike simple "Find & Replace" tools, this tool uses **Static Analysis (AST)** to understand scope, preventing accidental breakage of code structure or external references.

## Features

- **HTML Support**: Extracts and processes JS from `<script>` blocks and inline handlers (e.g., `onclick="..."`).
- **Scope Awareness**: Distinguishes between local variables, global variables, and class properties.
- **Safety System**: Detects "Shorthand Properties" and "Exports" that are dangerous to rename.
- **Excel Workflow**: Generates a TSV file for easy bulk-editing in Excel.
- **Conflict Prevention**: Prevents renaming variables to names that already exist in the same scope.
- **Auto-Setup**: Automatically checks for and installs necessary dependencies.

## Installation

1. **Install Node.js**:
   Download and install from [nodejs.org](https://nodejs.org/) (v18.0.0 or higher).
   _This is required for the tool to run._

2. **Clone/Download**:
   Download this repository to your local machine.

_(Note: You do not need to run `npm install` manually. The script will handle this for you.)_

## Quick Start

### 1. Prepare

Place your target HTML file in the `input/` folder.
_(Note: Only one .html file at a time)_

### 2. Run

Execute the main batch file:

```batch
run_renamer.bat
```

- **First Run**: If dependencies are missing, the tool will ask: `Would you like to run 'npm install' now?`. Type **yes** and press Enter.
- The tool will then extract JavaScript and generate a modification table.

### 3. Edit

Open `output/modification_table.tsv` in Excel (or any spreadsheet editor).

- **Filter** by `collision_type` to find safe identifiers.
- **Fill** the `new_name` column for identifiers you want to rename.
- **Leave empty** to keep the original name.

### 4. Apply

Return to the command prompt. When asked to continue, type `yes` and press Enter.

### 5. Result

The processed HTML is saved to `output/result.html`.

## Understanding the TSV Columns

The TSV file contains specific columns to help you decide what to rename.

| Column             | Description                                                       |
| ------------------ | ----------------------------------------------------------------- |
| **collision_type** | **CRITICAL**. Indicates renaming risks. See table below.          |
| **kind**           | The type of identifier (var, let, const, function, class, param). |
| **scope**          | The structural path of the scope.                                 |
| **old_name**       | The current name in the code.                                     |
| **new_name**       | **EDIT THIS**. Enter the new name here.                           |

### Safety Guide (collision_type)

| Value           | Meaning                                                                                                                                    | Action                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------- |
| **`shorthand`** | Used in Object Shorthand (e.g., `{ id }` or `const { data } = obj`). Renaming this changes the property key, which **will break the app**. | **DO NOT RENAME** (unless you know exactly what you are doing).  |
| **`export`**    | The variable is exported (`export const x`). Renaming breaks imports in other files.                                                       | **Caution**. Only rename if you update importing files manually. |
| **`global`**    | Defined in the global scope. Might be accessed by other scripts.                                                                           | **Caution**. Verify it is not used externally.                   |
| **`none`**      | Safe local variable.                                                                                                                       | **Safe to Rename**.                                              |

## Directory Structure

```text
### After Download

js-renamer/
├── run_renamer.bat               # Main tool (Automated setup & execution)
├── extract_js_from_html.bat      # Step 1 (manual)
├── extract_identifiers.bat       # Step 2 (manual)
├── rename_identifiers.bat        # Step 3 (manual)
├── reintegrate_to_html.bat       # Step 4 (manual)
├── package.json                  # Dependencies list
├── sample.html                   # Test sample
├── README.md                     # This file
└── node/                         # Node.js scripts
    ├── extract_js_from_html.js
    ├── extract_identifiers.js
    ├── rename_identifiers.js
    └── reintegrate_to_html.js

### After First Run (Auto-generated)

js-renamer/
├── package-lock.json             # Locked dependency versions
└── node_modules/                 # Installed libraries (~50MB)
    ├── espree/
    ├── eslint-scope/
    ├── escodegen/
    └── ...

```

## License

(c) 2026 GoodRelax. MIT License.

[https://github.com/GoodRelax](https://github.com/GoodRelax)

---
