#!/usr/bin/env bash
# run_multiqc.sh — Aggregate FastQC / Trim Galore / Cutadapt outputs into one HTML report.
#
# Usage:
#   bash run_multiqc.sh [-o OUTDIR] [-n TITLE] SEARCH_DIR
#
# Arguments:
#   SEARCH_DIR  Directory (or directories) to scan recursively for tool outputs.
#
# Options:
#   -o, --output OUTDIR   Where to write the report (default: SEARCH_DIR/multiqc_report)
#   -n, --name TITLE      Report title (default: "QC summary")
#       --force           Overwrite an existing report
#
# Examples:
#   bash run_multiqc.sh qc/
#   bash run_multiqc.sh -o reports/ -n "Project XYZ raw QC" qc/raw_fastqc/

set -euo pipefail

OUTDIR=""
TITLE="QC summary"
FORCE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    -o|--output) OUTDIR="$2"; shift 2 ;;
    -n|--name) TITLE="$2"; shift 2 ;;
    --force) FORCE="--force"; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) break ;;
  esac
done

if [[ $# -eq 0 ]]; then
  echo "Error: SEARCH_DIR is required. Run with -h for usage." >&2
  exit 1
fi

if ! command -v multiqc >/dev/null 2>&1; then
  echo "Error: multiqc not found on PATH. See references/installation.md." >&2
  exit 1
fi

SEARCH="$1"
[[ -z "$OUTDIR" ]] && OUTDIR="$SEARCH/multiqc_report"

mkdir -p "$OUTDIR"

echo "Running MultiQC on: $SEARCH"
echo "Output: $OUTDIR"
multiqc $FORCE -o "$OUTDIR" --title "$TITLE" "$SEARCH"

echo
report=$(find "$OUTDIR" -maxdepth 1 -name "*multiqc_report.html" -print -quit)
if [[ -n "$report" ]]; then
  echo "Done. Open: $report"
else
  echo "Done. Report HTML in: $OUTDIR"
fi
