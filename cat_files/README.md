# cat_files.bat

A robust Windows Batch utility designed to concatenate multiple files into a single document with metadata tags. This tool is particularly useful for preparing source code or logs for LLM (Large Language Model) analysis, as it clearly delimits the content of each file with its absolute path.

## Features

- **Metadata Tagging**: Wraps each file's content in markdown-style metadata tags containing the absolute file path.

- **Flexible Search**: Supports recursive searches and wildcard patterns (e.g., `**/*.txt`).

- **Encoding & Line Endings**:
- **Standard Mode**: Fast, binary-safe concatenation preserving original encodings and CRLF.

- **LF Mode (`-lf`)**: Automatically detects input encoding (UTF-8 or Shift-JIS) and converts the output to UTF-8 (No BOM) with LF line endings.

- **Safety**: Automatically skips the output file if it is located within the search path to prevent infinite loops.

---

## Usage

```bash
cat_files.bat -i <target_list> [-o <output_file>] [-lf]
```

### Arguments

| Argument | Description                                                                                       |
| -------- | ------------------------------------------------------------------------------------------------- |
| `-i`     | **Required**. Path to a text file containing the list of files or wildcard patterns to process.   |
| `-o`     | **Optional**. Path to the output file. Defaults to `cat_<target_list_name>.txt`.                  |
| `-lf`    | **Optional**. Triggers PowerShell mode to normalize output to UTF-8 (No BOM) and LF line endings. |

---

## Examples

**1. Basic concatenation:**

```bash
cat_files.bat -i list.txt

```

**2. Merging with LF normalization and custom output:**

```bash
cat_files.bat -i list.txt -o merged_project.txt -lf

```

**Example `list.txt` content:**

```text
src/*.cpp
include/**/*.h
docs/README.md
C:\Logs\app.log
```

---

## Development & Testing

The repository includes scripts to generate complex test environments (including Japanese filenames, deep nesting, and mixed encodings) to verify the tool's robustness:

- `gen_test_data_1.bat`: Basic Japanese filename and encoding tests.

- `gen_test_data_2.bat`: Deeply nested directory structures.

- `gen_test_data_3.bat`: "Evil" test cases involving spaces in paths and filenames.

---

### Limitation

- **PowerShell Execution Policy**: The script uses `-ExecutionPolicy Bypass`. While effective for portability, users in highly restricted corporate environments might need to manually unblock the script or adjust system policies.

- **Dependency**: The `-lf` mode requires PowerShell to be available in the system PATH (Standard on Windows 7 and later).

- **Temporary Files**: When using `-lf`, the script generates a temporary `.ps1` file in the current directory. If the script is interrupted, this file might remain and require manual deletion.

---

## License

(c) 2026 GoodRelax. MIT License.

[https://github.com/GoodRelax](https://github.com/GoodRelax)

---
