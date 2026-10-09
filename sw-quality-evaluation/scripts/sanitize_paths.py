"""Replace absolute local paths in a report directory with placeholders.

Usage: python sanitize_paths.py <REPORT_DIR> <CODE_DIR> [<SPEC_DIR>] [--tools <TOOLS_DIR>]

Every text file under REPORT_DIR is rewritten in place: the given roots become
<REPORT_DIR>, <CODE_DIR>, <SPEC_DIR> and <TOOLS_DIR>, and any remaining home
directory becomes ~. Both Windows (C:\\Users\\x, C:/Users/x) and POSIX-style
(/c/Users/x) spellings are handled. Absolute paths leak user names when a report
is shared. Prints the files changed and any absolute path it could not map.
"""
import pathlib
import re
import sys

TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".js", ".mjs",
                 ".cjs", ".py", ".html", ".xml", ".log"}


def spellings(path):
    """Return the spellings under which an absolute path may appear in tool output."""
    resolved = str(pathlib.Path(path).resolve())
    forward = resolved.replace("\\", "/")
    found = {resolved, forward, forward.replace("/", "\\\\")}
    match = re.match(r"^([A-Za-z]):/(.*)$", forward)
    if match:
        drive, rest = match.groups()
        found.add(f"/{drive.lower()}/{rest}")
        found.add(f"/{drive.upper()}/{rest}")
        found.add(f"{drive.lower()}:/{rest}")
        found.add(f"{drive.lower()}:\\{rest.replace('/', chr(92))}")
    return sorted(found, key=len, reverse=True)


def main():
    args = sys.argv[1:]
    tools_dir = None
    if "--tools" in args:
        index = args.index("--tools")
        tools_dir = args[index + 1]
        del args[index:index + 2]
    report_dir = pathlib.Path(args[0])
    roots = [("<REPORT_DIR>", args[0]), ("<CODE_DIR>", args[1])]
    if len(args) > 2:
        roots.append(("<SPEC_DIR>", args[2]))
    if tools_dir:
        roots.append(("<TOOLS_DIR>", tools_dir))
    home = pathlib.Path.home()
    roots.append(("~", str(home)))

    replacements = []
    for placeholder, root in roots:
        for spelling in spellings(root):
            replacements.append((spelling, placeholder))
    replacements.sort(key=lambda pair: len(pair[0]), reverse=True)

    leftover = re.compile(r"([A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+|/[a-z]/Users/[^/\s\"']+|/home/[^/\s\"']+)")
    changed = 0
    for path in report_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new_text = text
        for old, new in replacements:
            new_text = new_text.replace(old, new)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            changed += 1
        for hit in leftover.findall(new_text):
            print(f"UNMAPPED {path.relative_to(report_dir)}: {hit}")
    print(f"files rewritten: {changed}")


if __name__ == "__main__":
    main()
