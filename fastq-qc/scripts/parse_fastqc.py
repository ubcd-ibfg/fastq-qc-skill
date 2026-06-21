#!/usr/bin/env python3
"""
parse_fastqc.py — Read FastQC output zips and emit a structured per-sample summary.

FastQC writes both a `*_fastqc.html` (for humans) and a `*_fastqc.zip` (for machines).
This script unpacks the zip in memory, reads `summary.txt` and `fastqc_data.txt`, and
prints a compact summary that's easier to reason about than the raw HTML — including
plain-English flags ranked by severity.

Usage:
    python3 parse_fastqc.py <DIR_OR_ZIP> [<DIR_OR_ZIP> ...] [--json] [--csv OUT.csv]

Arguments may be:
- A directory containing one or more `*_fastqc.zip` files (recursively scanned), OR
- One or more `*_fastqc.zip` files directly.

Output: a human-readable summary by default. With `--json`, emits a JSON document
suitable for downstream tooling. With `--csv`, also writes a per-sample summary table.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ModuleResult:
    name: str
    status: str  # PASS / WARN / FAIL


@dataclass
class SampleReport:
    sample: str
    zip_path: str
    basic_stats: dict = field(default_factory=dict)
    modules: list[ModuleResult] = field(default_factory=list)
    flags: list[dict] = field(default_factory=list)  # severity-ranked human-readable flags

    def status_of(self, module_name: str) -> Optional[str]:
        for m in self.modules:
            if m.name == module_name:
                return m.status
        return None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def find_zips(paths: list[Path]) -> list[Path]:
    """Expand a mix of dirs and zip files into a flat list of *_fastqc.zip paths."""
    zips: list[Path] = []
    for p in paths:
        if p.is_dir():
            zips.extend(sorted(p.rglob("*_fastqc.zip")))
        elif p.is_file() and p.name.endswith("_fastqc.zip"):
            zips.append(p)
        else:
            print(f"Warning: {p} is not a directory or *_fastqc.zip — skipping", file=sys.stderr)
    return zips


def parse_summary(content: str) -> list[ModuleResult]:
    """`summary.txt` is tab-separated: STATUS \\t MODULE \\t FILENAME"""
    modules = []
    for line in content.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            modules.append(ModuleResult(name=parts[1].strip(), status=parts[0].strip()))
    return modules


def parse_basic_stats(content: str) -> dict:
    """Extract the >>Basic Statistics<< section from fastqc_data.txt."""
    stats: dict = {}
    in_section = False
    for line in content.splitlines():
        if line.startswith(">>Basic Statistics"):
            in_section = True
            continue
        if in_section:
            if line.startswith(">>END_MODULE"):
                break
            if line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                key, val = parts
                stats[key.strip()] = val.strip()
    return stats


def extract_total_duplication(content: str) -> Optional[float]:
    """The duplication module includes a #Total Deduplicated Percentage header line."""
    for line in content.splitlines():
        if line.startswith("#Total Deduplicated Percentage"):
            parts = line.split("\t")
            if len(parts) >= 2:
                try:
                    dedup_pct = float(parts[1])
                    return round(100.0 - dedup_pct, 2)  # duplication % = 100 - dedup %
                except ValueError:
                    return None
    return None


def parse_fastqc_zip(zip_path: Path) -> SampleReport:
    sample = zip_path.name.replace("_fastqc.zip", "")
    report = SampleReport(sample=sample, zip_path=str(zip_path))

    with zipfile.ZipFile(zip_path) as zf:
        # Files inside the zip are namespaced under <sample>_fastqc/
        inner_dir = f"{sample}_fastqc"
        try:
            summary = zf.read(f"{inner_dir}/summary.txt").decode("utf-8")
            data = zf.read(f"{inner_dir}/fastqc_data.txt").decode("utf-8")
        except KeyError as e:
            print(f"Warning: {zip_path} missing expected file {e}", file=sys.stderr)
            return report

        report.modules = parse_summary(summary)
        report.basic_stats = parse_basic_stats(data)
        dup = extract_total_duplication(data)
        if dup is not None:
            report.basic_stats["Approx. duplication %"] = f"{dup:.2f}"

    return report


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

# Severity ranks: higher = more important to act on. Used to sort flags.
SEVERITY = {"FAIL": 3, "WARN": 2, "PASS": 0}

# Module → (severity rule, plain-English explanation when triggered).
# These are concise. The full nuance lives in references/interpretation.md.
MODULE_NOTES = {
    "Per base sequence quality": {
        "FAIL": "Per-base quality drops below acceptable thresholds. If the drop is at the 3′ end only, quality-trim. If at the 5′ end or middle, investigate the sequencing run.",
        "WARN": "Per-base quality dips in places. Often safe at the 3′ end; check the plot before trimming.",
    },
    "Per tile sequence quality": {
        "FAIL": "Specific flowcell tiles show poor quality. Consider filtering reads from those tiles.",
        "WARN": "Some flowcell tiles deviate from the rest. Often a transient flowcell artifact.",
    },
    "Per sequence quality scores": {
        "FAIL": "A meaningful fraction of reads have low mean quality. Check for a bimodal distribution (often R2 in paired-end).",
        "WARN": "Mean-quality distribution has a low-quality shoulder.",
    },
    "Per base sequence content": {
        "FAIL": "Base composition is biased. Expected in RNA-seq (random hexamer priming, first ~12 bp), amplicon, and bisulfite libraries. Concerning if persistent across the whole read.",
        "WARN": "Some position-specific base bias. Usually benign for the first few bases.",
    },
    "Per sequence GC content": {
        "FAIL": "GC distribution deviates from expected. Bimodal → contamination. Shifted → wrong organism or strong enrichment.",
        "WARN": "GC distribution slightly off expected — worth a glance but often benign.",
    },
    "Per base N content": {
        "FAIL": "Significant N (no-call) content. Check if a specific position can be hard-trimmed.",
        "WARN": "Some N content at specific positions.",
    },
    "Sequence Length Distribution": {
        "FAIL": "Read lengths vary unexpectedly. Common after upstream trimming; concerning on raw fixed-length runs.",
        "WARN": "Read lengths are not uniform. Often benign (FastQC WARNs on any non-uniform distribution).",
    },
    "Sequence Duplication Levels": {
        "FAIL": "High sequence duplication. Expected in ChIP-seq IP, amplicon, and small-RNA libraries; concerning in deep unbiased libraries (low complexity).",
        "WARN": "Elevated duplication. Handle after alignment (e.g., MarkDuplicates) rather than at the FASTQ stage.",
    },
    "Overrepresented sequences": {
        "FAIL": "Sequences appear far more often than expected. Adapter sequences → trim. rRNA → failed depletion. Binding motifs in ChIP-seq IP → expected.",
        "WARN": "Some over-represented sequences detected. Check the table for adapter or contaminant hits.",
    },
    "Adapter Content": {
        "FAIL": "Adapter readthrough is significant. Trim with Trim Galore or fastp before alignment.",
        "WARN": "Some adapter contamination detected. Trimming recommended.",
    },
    "Kmer Content": {
        "FAIL": "K-mer enrichment detected. Expected and good in ChIP-seq IP (binding motifs). Concerning in input/RNA-seq/ATAC-seq.",
        "WARN": "Some positional K-mer enrichment.",
    },
}


def derive_flags(report: SampleReport) -> list[dict]:
    """Turn module statuses into human-readable flags ranked by severity."""
    flags = []
    for mod in report.modules:
        if mod.status == "PASS":
            continue
        note = MODULE_NOTES.get(mod.name, {}).get(mod.status, "Investigate this module manually.")
        flags.append({
            "severity": mod.status,
            "module": mod.name,
            "rank": SEVERITY[mod.status],
            "explanation": note,
        })
    flags.sort(key=lambda f: -f["rank"])
    return flags


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_human(reports: list[SampleReport]) -> None:
    if not reports:
        print("No FastQC zip files found.")
        return

    # Each sample falls into exactly one bucket. FAILs take precedence over WARNs.
    n_fail = sum(1 for r in reports if any(m.status == "FAIL" for m in r.modules))
    n_warn_only = sum(1 for r in reports
                      if not any(m.status == "FAIL" for m in r.modules)
                      and any(m.status == "WARN" for m in r.modules))
    n_clean = len(reports) - n_fail - n_warn_only

    print(f"Parsed {len(reports)} FastQC report(s): "
          f"{n_clean} clean, {n_warn_only} with WARNs only, {n_fail} with at least one FAIL")
    print("=" * 78)

    for r in reports:
        print(f"\nSample: {r.sample}")
        print("-" * 78)

        if r.basic_stats:
            interesting = ["Total Sequences", "Sequence length", "%GC", "Approx. duplication %"]
            for key in interesting:
                if key in r.basic_stats:
                    print(f"  {key:30s} {r.basic_stats[key]}")

        if r.flags:
            print(f"\n  Flags ({len(r.flags)}):")
            for f in r.flags:
                print(f"    [{f['severity']}] {f['module']}")
                # wrap the explanation at ~70 chars for readability
                expl = f["explanation"]
                while expl:
                    chunk, expl = expl[:72], expl[72:]
                    if expl and not expl.startswith(" "):
                        # break at last space in chunk
                        sp = chunk.rfind(" ")
                        if sp > 30:
                            expl = chunk[sp + 1:] + expl
                            chunk = chunk[:sp]
                    print(f"        {chunk.strip()}")
        else:
            print("\n  No WARN or FAIL — all modules PASS.")

    print()


def to_json(reports: list[SampleReport]) -> str:
    payload = []
    for r in reports:
        d = asdict(r)
        # Move flags to the top level for easier downstream consumption
        d["flags"] = r.flags
        d["modules"] = [asdict(m) for m in r.modules]
        payload.append(d)
    return json.dumps(payload, indent=2)


def write_csv(reports: list[SampleReport], path: Path) -> None:
    fieldnames = ["sample", "total_reads", "read_length", "pct_gc",
                  "approx_dup_pct", "num_warn", "num_fail", "flagged_modules"]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in reports:
            bs = r.basic_stats
            flagged = [m.name for m in r.modules if m.status in ("WARN", "FAIL")]
            w.writerow({
                "sample": r.sample,
                "total_reads": bs.get("Total Sequences", ""),
                "read_length": bs.get("Sequence length", ""),
                "pct_gc": bs.get("%GC", ""),
                "approx_dup_pct": bs.get("Approx. duplication %", ""),
                "num_warn": sum(1 for m in r.modules if m.status == "WARN"),
                "num_fail": sum(1 for m in r.modules if m.status == "FAIL"),
                "flagged_modules": "; ".join(flagged),
            })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="Directories or *_fastqc.zip files to parse")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output")
    ap.add_argument("--csv", type=Path, help="Also write a per-sample summary CSV to this path")
    args = ap.parse_args()

    zips = find_zips([Path(p) for p in args.paths])
    if not zips:
        print("Error: no *_fastqc.zip files found at the given paths.", file=sys.stderr)
        return 1

    reports: list[SampleReport] = []
    for z in zips:
        r = parse_fastqc_zip(z)
        r.flags = derive_flags(r)
        reports.append(r)

    if args.json:
        print(to_json(reports))
    else:
        print_human(reports)

    if args.csv:
        write_csv(reports, args.csv)
        print(f"CSV summary written to {args.csv}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
