content = open("index.html", encoding="utf-8").read()

checks = [
    ("DOCTYPE present",       "<!doctype html>" in content.lower()),
    ("pako inlined",          "pako.min.js" not in content and "pako 2.1.0" in content),
    ("no import statements",  "import {" not in content),
    ("no export statements",  "export {" not in content
                              and "export class" not in content
                              and "export function" not in content
                              and "export const" not in content),
    ("encodeExecute defined", "async function encodeExecute(" in content),
    ("decodeExecute defined", "async function decodeExecute(" in content),
    ("encodeExecute called",  "await encodeExecute(" in content),
    ("decodeExecute called",  "await decodeExecute(" in content),
    ("switchTab defined",     "window.switchTab" in content),
    ("GrtmError defined",     "class GrtmError" in content),
    ("STANDARD_RESOLUTIONS",  "const STANDARD_RESOLUTIONS" in content),
    ("single module script",  content.count('<script type="module">') == 1),
    ("no src= on module",     '<script type="module" src=' not in content),
    ("stale comment removed", "main.js on page load" not in content),
]

all_ok = True
for name, ok in checks:
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if not ok:
        all_ok = False

print()
print("All checks passed." if all_ok else "SOME CHECKS FAILED.")
