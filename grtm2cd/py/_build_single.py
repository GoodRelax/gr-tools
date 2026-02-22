import re
import os

base = r"c:\Users\good_\OneDrive\Documents\GitHub\gr-tools\grtm2cd"


def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def strip_module_syntax(content, rename_execute_to=None):
    lines = content.split("\n")
    result = []
    in_multiline_import = False
    for line in lines:
        if in_multiline_import:
            if re.match(r"^\}\s*from\s+['\"]", line):
                in_multiline_import = False
            continue
        if re.match(r"^import\s+", line):
            if "{" in line and "}" not in line:
                in_multiline_import = True
            continue
        if re.match(r"^export\s+\{[^}]*\}\s*;?\s*$", line):
            continue
        line = re.sub(
            r"^export\s+((?:async\s+)?(?:class|function|const|let|var)\b)",
            r"\1",
            line,
        )
        result.append(line)
    content = "\n".join(result)
    if rename_execute_to:
        content = content.replace(
            "async function execute(", f"async function {rename_execute_to}(", 1
        )
    return content


files = [
    (os.path.join(base, "assets", "js", "domain", "errors.js"),              None),
    (os.path.join(base, "assets", "js", "domain", "standardResolutions.js"), None),
    (os.path.join(base, "assets", "js", "domain", "lsbEngine.js"),           None),
    (os.path.join(base, "assets", "js", "domain", "stripingEngine.js"),      None),
    (os.path.join(base, "assets", "js", "domain", "capacityCalc.js"),        None),
    (os.path.join(base, "assets", "js", "domain", "matryoshkaPacker.js"),    None),
    (os.path.join(base, "assets", "js", "adapter", "compressorAdapter.js"),  None),
    (os.path.join(base, "assets", "js", "adapter", "cryptoAdapter.js"),      None),
    (os.path.join(base, "assets", "js", "adapter", "imageAdapter.js"),       None),
    (os.path.join(base, "assets", "js", "usecase", "encodeUseCase.js"),      "encodeExecute"),
    (os.path.join(base, "assets", "js", "usecase", "decodeUseCase.js"),      "decodeExecute"),
    (os.path.join(base, "assets", "js", "main.js"),                          None),
]

pako_content = read_file(os.path.join(base, "assets", "js", "pako.min.js"))

js_parts = []
for path, rename in files:
    content = read_file(path)
    processed = strip_module_syntax(content, rename)
    label = os.path.basename(path)
    js_parts.append(f"// === {label} ===\n{processed}")

combined_js = "\n\n".join(js_parts)

html = read_file(os.path.join(base, "index-multi-files.html"))

old_scripts = (
    "    <!-- pako loaded as global script (non-module) per C-5 -->\n"
    '    <script src="assets/js/pako.min.js"></script>\n'
    "    <!-- main.js as ES module per C-6 -->\n"
    '    <script type="module" src="assets/js/main.js"></script>'
)

new_scripts = (
    f"    <script>\n{pako_content}\n    </script>\n"
    f"    <script type=\"module\">\n{combined_js}\n    </script>"
)

result = html.replace(old_scripts, new_scripts)

if result == html:
    print("ERROR: replacement did not occur — check old_scripts string")
    exit(1)

result = result.replace(
    "\n    <!-- Populated dynamically by main.js on page load (\u00a76.3) -->",
    "",
)

out_path = os.path.join(base, "index.html")
with open(out_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(result)

size_kb = os.path.getsize(out_path) / 1024
print(f"Done. index.html created ({size_kb:.1f} KB)")
