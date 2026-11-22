"""Sanity-check M code in generated TMDL partitions: balanced delimiters, step chaining."""
import os
import re

TABLES_DIR = r"C:\Users\sharm\Downloads\powerbi\MandiRainfallDashboard\MandiRainfallDashboard.SemanticModel\definition\tables"

fail = False
for fn in sorted(os.listdir(TABLES_DIR)):
    path = os.path.join(TABLES_DIR, fn)
    text = open(path, encoding="utf-8").read()
    if "= calculated" in text:
        print(f"{fn}: OK (calculated partition)")
        continue
    m = re.search(r"source =\n(.*)$", text, re.S)
    if not m:
        print(f"{fn}: NO PARTITION SOURCE FOUND")
        fail = True
        continue
    code = m.group(1)
    lines = code.split("\n")
    body = "\n".join(re.sub(r"^\t{3}", "", l) for l in lines)
    errs = []
    for a, b in [("{", "}"), ("(", ")"), ("[", "]")]:
        if body.count(a) != body.count(b):
            errs.append(f"unbalanced {a}{b}: {body.count(a)} vs {body.count(b)}")
    if body.count('"') % 2 != 0:
        errs.append("unbalanced quotes")
    steps = re.findall(r"^    (\w+) = ", body, re.M)
    result = re.search(r"^in\n    (\w+)\s*$", body, re.M)
    if not result:
        errs.append("no result identifier")
    else:
        if result.group(1) not in steps:
            errs.append(f"result '{result.group(1)}' not a step")
    # each step after the first must mention the previous step name
    for i in range(1, len(steps)):
        line = re.search(rf"^    {steps[i]} = (.*)$", body, re.M)
        if line and not re.search(rf"\b{steps[i-1]}\b", line.group(1)):
            errs.append(f"step '{steps[i]}' does not reference '{steps[i-1]}'")
    if errs:
        fail = True
        print(f"{fn}: FAIL -> " + "; ".join(errs))
    else:
        print(f"{fn}: OK ({len(steps)} steps chained)")

print("M SANITY:", "FAIL" if fail else "PASS")
