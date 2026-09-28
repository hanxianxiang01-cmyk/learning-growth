#!/usr/bin/env python3
"""Validate that cached Summary totals inside the XLSX match Backlog detail.

Why this exists:
Excel formula cells store both the formula and a cached <v> value. Python readers
that do not calculate formulas may return only that cache. Therefore, after any
Backlog-detail edit, the workbook MUST be recalculated before commit/release.

Usage:
    python 06_validate_backlog_summary_cache.py 05_Sprint_Backlog_v1.3.1.xlsx

Exit codes:
    0 = cached Summary matches independently recomputed detail totals
    1 = mismatch / missing formula / missing cached value / malformed workbook
"""
from __future__ import annotations

import argparse
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import PurePosixPath

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _shared_strings(zf: zipfile.ZipFile):
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall("m:si", NS):
        out.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))
    return out


def _sheet_paths(zf: zipfile.ZipFile):
    wb = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels.findall(f"{{{REL_NS}}}Relationship")}
    out = {}
    for s in wb.find("m:sheets", NS):
        rid = s.attrib[f"{{{NS['r']}}}id"]
        target = relmap[rid].lstrip("/")
        if not target.startswith("xl/"):
            target = str(PurePosixPath("xl") / target)
        out[s.attrib["name"]] = target
    return out


def _cell_value(cell, shared):
    ctype = cell.attrib.get("t")
    if ctype == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//m:t", NS))
    v = cell.find("m:v", NS)
    if v is None:
        return None
    raw = v.text or ""
    if ctype == "s":
        return shared[int(raw)]
    if ctype in {"str", "e"}:
        return raw
    try:
        f = float(raw)
        return int(f) if f.is_integer() else f
    except ValueError:
        return raw


def _read_sheet(zf, path, shared):
    root = ET.fromstring(zf.read(path))
    cells = {}
    for c in root.findall(".//m:c", NS):
        cells[c.attrib["r"]] = {
            "value": _cell_value(c, shared),
            "formula": (c.find("m:f", NS).text if c.find("m:f", NS) is not None else None),
            "cache_present": c.find("m:v", NS) is not None,
        }
    return cells


def _col(addr: str):
    return "".join(ch for ch in addr if ch.isalpha())


def _row(addr: str):
    return int("".join(ch for ch in addr if ch.isdigit()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsx")
    args = ap.parse_args()

    with zipfile.ZipFile(args.xlsx) as zf:
        shared = _shared_strings(zf)
        paths = _sheet_paths(zf)
        for required in ("Backlog", "Summary"):
            if required not in paths:
                print(f"FAIL: missing sheet {required}")
                return 1
        backlog = _read_sheet(zf, paths["Backlog"], shared)
        summary = _read_sheet(zf, paths["Summary"], shared)

    # Recompute detail totals from Backlog.
    detail = OrderedDict()
    max_row = max((_row(a) for a in backlog), default=1)
    for r in range(2, max_row + 1):
        epic = backlog.get(f"A{r}", {}).get("value")
        if not epic:
            continue
        priority = backlog.get(f"D{r}", {}).get("value")
        points = backlog.get(f"G{r}", {}).get("value") or 0
        bucket = detail.setdefault(str(epic), {"stories": 0, "points": 0, "P0": 0, "P1": 0, "P2": 0})
        bucket["stories"] += 1
        bucket["points"] += int(points)
        if priority in ("P0", "P1", "P2"):
            bucket[str(priority)] += 1

    failures = []
    # Compare rows in Summary A:F until blank epic.
    for r in range(2, 200):
        epic = summary.get(f"A{r}", {}).get("value")
        if not epic:
            if r > 2:
                break
            continue
        epic = str(epic)
        if epic not in detail:
            failures.append(f"Summary A{r} epic {epic!r} not present in Backlog detail")
            continue
        expected = [detail[epic]["stories"], detail[epic]["points"], detail[epic]["P0"], detail[epic]["P1"], detail[epic]["P2"]]
        for col, exp in zip("BCDEF", expected):
            cell = summary.get(f"{col}{r}")
            if not cell:
                failures.append(f"Summary {col}{r} missing")
                continue
            if not cell["formula"]:
                failures.append(f"Summary {col}{r} is not a formula cell")
            if not cell["cache_present"]:
                failures.append(f"Summary {col}{r} cached <v> is missing")
            actual = cell["value"]
            if actual != exp:
                failures.append(f"Summary {col}{r} cache={actual!r}, expected={exp!r} from Backlog")

    summary_epics = {str(summary.get(f"A{r}", {}).get("value")) for r in range(2, 200) if summary.get(f"A{r}", {}).get("value")}
    for epic in detail:
        if epic not in summary_epics:
            failures.append(f"Backlog epic {epic!r} missing from Summary")

    if failures:
        print("FAIL: XLSX formula-cache Gate did not pass")
        for f in failures:
            print(" -", f)
        print("Action: recalculate workbook with Excel/LibreOffice/artifact_tool, refresh caches, then rerun this check.")
        return 1

    print("PASS: Summary formula caches match independently recomputed Backlog detail totals")
    for epic, v in detail.items():
        print(f" - {epic}: stories={v['stories']}, points={v['points']}, P0={v['P0']}, P1={v['P1']}, P2={v['P2']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
