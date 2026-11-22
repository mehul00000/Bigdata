"""Validate generated PBIP JSON files against official Microsoft JSON schemas."""
import json
import os
import urllib.request

import referencing
import referencing.jsonschema
from jsonschema import Draft7Validator

OUT = r"C:\Users\sharm\Downloads\powerbi\MandiRainfallDashboard"
SM = os.path.join(OUT, "MandiRainfallDashboard.SemanticModel")
REP = os.path.join(OUT, "MandiRainfallDashboard.Report")
S = "https://developer.microsoft.com/json-schemas/fabric/"

FETCHED = {}


def retrieve(uri):
    if uri in FETCHED:
        return FETCHED[uri]
    print(f"  fetching: {uri}")
    with urllib.request.urlopen(uri, timeout=30) as r:
        contents = json.load(r)
    res = referencing.jsonschema.DRAFT7.create_resource(contents)
    FETCHED[uri] = res
    return res


registry = referencing.Registry(retrieve=retrieve)


def validate_file(path, schema_url, extra_schema_urls=()):
    with open(path, encoding="utf-8") as f:
        inst = json.load(f)
    results = []
    for url in [schema_url, *extra_schema_urls]:
        with urllib.request.urlopen(url, timeout=30) as r:
            schema = json.load(r)
        v = Draft7Validator(schema, registry=registry)
        errs = sorted(v.iter_errors(inst), key=lambda e: list(e.path))
        if errs:
            results.append((url, errs))
    return results


jobs = []

jobs.append((os.path.join(OUT, "MandiRainfallDashboard.pbip"), S + "pbip/pbipProperties/1.0.0/schema.json", []))
jobs.append((os.path.join(REP, "definition.pbir"), S + "item/report/definitionProperties/2.0.0/schema.json", []))
jobs.append((os.path.join(SM, "definition.pbism"), S + "item/semanticModel/definitionProperties/1.0.0/schema.json", []))
jobs.append((os.path.join(REP, "definition", "report.json"), S + "item/report/definition/report/3.2.0/schema.json",
             [S + "item/report/definition/report/3.3.0/schema.json"]))
jobs.append((os.path.join(REP, "definition", "version.json"), S + "item/report/definition/versionMetadata/1.0.0/schema.json", []))
jobs.append((os.path.join(REP, "definition", "pages", "pages.json"),
             S + "item/report/definition/pagesMetadata/1.0.0/schema.json", []))

pages_dir = os.path.join(REP, "definition", "pages")
for pid in os.listdir(pages_dir):
    pdir = os.path.join(pages_dir, pid)
    if os.path.isdir(pdir):
        jobs.append((os.path.join(pdir, "page.json"), S + "item/report/definition/page/2.0.0/schema.json",
                     [S + "item/report/definition/page/2.1.0/schema.json"]))
        for vid in os.listdir(os.path.join(pdir, "visuals")):
            jobs.append((os.path.join(pdir, "visuals", vid, "visual.json"),
                         S + "item/report/definition/visualContainer/2.9.0/schema.json",
                         [S + "item/report/definition/visualContainer/2.13.0/schema.json"]))

total = 0
failed = 0
for path, url, extras in jobs:
    total += 1 + len(extras)
    try:
        results = validate_file(path, url, extras)
    except Exception as e:
        print(f"ERROR loading {os.path.basename(path)}: {e}")
        failed += 1
        continue
    if results:
        # ignore $schema-const mismatch when cross-checking content against other versions
        real_results = [(u, [e for e in errs if list(e.absolute_path) != ["$schema"]]) for u, errs in results]
        real_results = [(u, errs) for u, errs in real_results if errs]
        if not real_results:
            continue
        failed += 1
        for url_used, errs in real_results:
            for e in errs[:5]:
                loc = ".".join(str(p) for p in e.absolute_path)[:120]
                print(f"FAIL {os.path.basename(path)} @ {loc}\n     {e.message[:220]}")
print(f"\n{total} validations across {len(jobs)} files -> {'ALL PASS' if failed == 0 else str(failed) + ' FAILED'}")
