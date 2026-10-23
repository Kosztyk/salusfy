#!/usr/bin/env python3
"""Offline HACS readiness checks for Salusfy."""
import json
import re
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def validate(root=ROOT):
    errors=[]
    for filename in ("README.md","LICENSE.txt","hacs.json","docs/licenta-originala-ro.md",
                     ".github/workflows/validate.yml","custom_components/salus/__init__.py",
                     "custom_components/salus/manifest.json","custom_components/salus/brand/icon.png"):
        if not (root/filename).is_file(): errors.append(f"Missing: {filename}")
    root_components=root/"custom_components"
    if root_components.is_dir() and [p.name for p in root_components.iterdir() if p.is_dir()]!=["salus"]:
        errors.append("Unexpected custom_components directory")
    manifest_file=root/"custom_components/salus/manifest.json"
    if manifest_file.is_file():
        m=json.loads(manifest_file.read_text())
        if m.get("domain")!="salus" or m.get("version")!="1.2.1":
            errors.append("Incorrect domain/version")
        if m.get("codeowners")!=["@Kosztyk"]:
            errors.append("Missing correct codeowner")
        if list(m) != ["domain","name"]+sorted(k for k in m if k not in ("domain","name")):
            errors.append("Manifest order invalid")
        if not re.fullmatch(r"\d+\.\d+\.\d+",str(m.get("version",""))):
            errors.append("Invalid version")
    license_file=root/"LICENSE.txt"
    if license_file.is_file() and not license_file.read_text().startswith("MIT License"):
        errors.append("MIT license text not standardized")
    return errors

if __name__=="__main__":
    errs=validate()
    for e in errs: print(e,file=sys.stderr)
    if errs: raise SystemExit(1)
    print("PASS: Salusfy HACS metadata")
