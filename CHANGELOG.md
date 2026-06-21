# Changelog

All notable changes to this skill will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-06-21

Initial release.

### Added

- `SKILL.md` with the 7-step QC workflow (inputs → tool check → FastQC → interpretation → trim decision → trim → MultiQC → summary).
- `references/interpretation.md` — per-module FastQC field guide covering all 12 standard modules with assay-specific notes for ChIP-seq, ATAC-seq, and RNA-seq.
- `references/installation.md` — install paths via conda/mamba, apt, Homebrew, pip, and manual download.
- `references/fastq-format.md` — FASTQ format and Phred encoding primer.
- `scripts/run_fastqc.sh` — FastQC wrapper with automatic thread sizing.
- `scripts/trim_reads.sh` — Trim Galore wrapper supporting single-end and paired-end batches.
- `scripts/run_multiqc.sh` — MultiQC wrapper.
- `scripts/parse_fastqc.py` — parser that turns `*_fastqc.zip` archives into structured per-sample summaries with severity-ranked flags; supports text, JSON, and CSV output.
- End-to-end validation on 4 paired-end yeast RNA-seq FASTQs from the nf-core test datasets.
- Example MultiQC report and summary CSV under `examples/`.
- Pre-packaged `.skill` archive under `dist/` for one-click upload to Claude.ai.
