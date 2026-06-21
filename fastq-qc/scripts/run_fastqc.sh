#!/usr/bin/env bash
# run_fastqc.sh — Run FastQC on one or more FASTQ files with a sensible thread count.
#
# Usage:
#   bash run_fastqc.sh [-o OUTDIR] [-t THREADS] FILE [FILE ...]
#
# Defaults:
#   OUTDIR  = ./fastqc_results
#   THREADS = min(number of files, number of CPU cores, 8)
#
# Examples:
#   bash run_fastqc.sh sample.fastq.gz
#   bash run_fastqc.sh -o qc/raw raw/*.fastq.gz
#   bash run_fastqc.sh -o qc/raw -t 8 raw/*.fastq.gz

set -euo pipefail

OUTDIR="./fastqc_results"
THREADS=""

while getopts ":o:t:h" opt; do
  case $opt in
    o) OUTDIR="$OPTARG" ;;
    t) THREADS="$OPTARG" ;;
    h) sed -n '2,16p' "$0"; exit 0 ;;
    \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

if [[ $# -eq 0 ]]; then
  echo "Error: no input files given. Run with -h for usage." >&2
  exit 1
fi

# Verify FastQC is on PATH
if ! command -v fastqc >/dev/null 2>&1; then
  echo "Error: fastqc not found on PATH. See references/installation.md." >&2
  exit 1
fi

# Pick threads if not provided: min(file count, cores, 8). 8 is FastQC's practical ceiling
# per process — beyond that it just consumes more RAM without speeding up.
if [[ -z "$THREADS" ]]; then
  CORES=$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)
  NFILES=$#
  THREADS=$(( NFILES < CORES ? NFILES : CORES ))
  THREADS=$(( THREADS < 8 ? THREADS : 8 ))
fi

mkdir -p "$OUTDIR"

echo "Running FastQC: $# file(s), $THREADS thread(s), output -> $OUTDIR"
fastqc -o "$OUTDIR" -t "$THREADS" "$@"

echo "Done. Reports in $OUTDIR:"
ls -1 "$OUTDIR"/*_fastqc.html 2>/dev/null | sed 's/^/  /'
