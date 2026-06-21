#!/usr/bin/env bash
# trim_reads.sh — Run Trim Galore on a directory of FASTQ files (single-end or paired-end).
#
# Usage:
#   bash trim_reads.sh -i INDIR -o OUTDIR [--paired] [-q QUAL] [-l MINLEN] [-j JOBS]
#
# Options:
#   -i, --input INDIR     Directory containing input FASTQ files (.fastq.gz or .fq.gz)
#   -o, --output OUTDIR   Directory for trimmed reads and reports
#       --paired          Treat inputs as paired-end (expects matching R1/R2 by name)
#   -q, --quality QUAL    Phred quality cutoff (default: 20)
#   -l, --length MINLEN   Discard reads shorter than MINLEN after trimming (default: 20)
#   -j, --jobs JOBS       Parallel Trim Galore processes (default: 4). Each uses ~2 cores.
#       --no-fastqc       Skip the post-trim FastQC run
#
# Examples:
#   bash trim_reads.sh -i raw/ -o qc/trimmed/
#   bash trim_reads.sh -i raw/ -o qc/trimmed/ --paired -q 25 -l 30

set -euo pipefail

INDIR=""
OUTDIR=""
PAIRED=0
QUAL=20
MINLEN=20
JOBS=4
RUN_FASTQC="--fastqc"

while [[ $# -gt 0 ]]; do
  case $1 in
    -i|--input) INDIR="$2"; shift 2 ;;
    -o|--output) OUTDIR="$2"; shift 2 ;;
    --paired) PAIRED=1; shift ;;
    -q|--quality) QUAL="$2"; shift 2 ;;
    -l|--length) MINLEN="$2"; shift 2 ;;
    -j|--jobs) JOBS="$2"; shift 2 ;;
    --no-fastqc) RUN_FASTQC=""; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$INDIR" || -z "$OUTDIR" ]]; then
  echo "Error: -i and -o are required. Run with -h for usage." >&2
  exit 1
fi

for t in trim_galore cutadapt; do
  if ! command -v $t >/dev/null 2>&1; then
    echo "Error: $t not found on PATH. See references/installation.md." >&2
    exit 1
  fi
done

mkdir -p "$OUTDIR"

# Find input files. Support .fastq.gz, .fq.gz, .fastq, .fq.
mapfile -t ALL_FILES < <(find "$INDIR" -maxdepth 1 -type f \
  \( -name "*.fastq.gz" -o -name "*.fq.gz" -o -name "*.fastq" -o -name "*.fq" \) | sort)

if [[ ${#ALL_FILES[@]} -eq 0 ]]; then
  echo "Error: no FASTQ files found in $INDIR" >&2
  exit 1
fi

echo "Found ${#ALL_FILES[@]} FASTQ file(s) in $INDIR"
echo "Quality cutoff: Q$QUAL  Min length: $MINLEN bp  Jobs: $JOBS"

if [[ $PAIRED -eq 1 ]]; then
  # Pair files by stripping _R1/_R2 or _1/_2 suffix
  declare -A R1 R2
  for f in "${ALL_FILES[@]}"; do
    base=$(basename "$f")
    if [[ "$base" =~ _R1[._] ]] || [[ "$base" =~ _1\.f(ast)?q ]]; then
      stem=$(echo "$base" | sed -E 's/_R1[._]/_/; s/_1(\.f(ast)?q)/\1/')
      R1[$stem]=$f
    elif [[ "$base" =~ _R2[._] ]] || [[ "$base" =~ _2\.f(ast)?q ]]; then
      stem=$(echo "$base" | sed -E 's/_R2[._]/_/; s/_2(\.f(ast)?q)/\1/')
      R2[$stem]=$f
    fi
  done

  if [[ ${#R1[@]} -eq 0 ]]; then
    echo "Error: --paired set but no R1/R2 pairs detected. Check file naming." >&2
    exit 1
  fi

  echo "Paired-end mode: ${#R1[@]} pair(s) detected"

  # Use xargs for parallelism. Each trim_galore call gets one pair.
  for stem in "${!R1[@]}"; do
    if [[ -z "${R2[$stem]:-}" ]]; then
      echo "Warning: $stem has R1 but no matching R2 — skipping" >&2
      continue
    fi
    printf '%s\t%s\n' "${R1[$stem]}" "${R2[$stem]}"
  done | xargs -P "$JOBS" -L 1 bash -c '
    r1="$0"; r2="$1"
    echo "Trimming pair: $(basename "$r1") + $(basename "$r2")"
    trim_galore --paired -q '"$QUAL"' --length '"$MINLEN"' '"$RUN_FASTQC"' \
      -o "'"$OUTDIR"'" "$r1" "$r2"
  '

else
  echo "Single-end mode"
  printf '%s\n' "${ALL_FILES[@]}" | xargs -P "$JOBS" -I {} bash -c '
    echo "Trimming: $(basename "$1")"
    trim_galore -q '"$QUAL"' --length '"$MINLEN"' '"$RUN_FASTQC"' \
      -o "'"$OUTDIR"'" "$1"
  ' _ {}
fi

echo
echo "Done. Outputs in $OUTDIR:"
ls -1 "$OUTDIR" | head -20 | sed 's/^/  /'
echo "  (showing first 20)"
