---
name: fastq-qc
description: Run quality control on FASTQ sequencing files using FastQC, interpret the report, optionally trim adapters and low-quality bases with Trim Galore, and aggregate multi-sample reports with MultiQC. Use whenever the user mentions FASTQ files, .fq/.fastq/.fq.gz/.fastq.gz, read quality, FastQC, MultiQC, adapter trimming, Trim Galore, Phred scores, sequencing QC, raw read assessment, or wants to inspect or clean up reads before alignment — even if they don't name a specific tool. Also use when the user is reviewing ChIP-seq, ATAC-seq, RNA-seq, or any NGS data at the raw-read stage.
---

# FASTQ Quality Control

End-to-end quality control for FASTQ sequencing reads, following the FastQC interpretation framework taught by the Harvard Chan Bioinformatics Core ([HBC ChIP-seq tutorial](https://hbctraining.github.io/Investigating-chromatin-biology-ChIPseq/lessons/03_QC_FASTQC.html)).

The skill covers:

1. Running **FastQC** on one or many FASTQ files (single-end or paired-end, gzipped or not).
2. **Interpreting** the report module-by-module, with context-aware notes for ChIP-seq, ATAC-seq, and RNA-seq.
3. **Trimming** adapters and low-quality bases with **Trim Galore** when QC indicates it.
4. **Aggregating** results across samples with **MultiQC**.

## Workflow

```
[ ] 0. Identify inputs: list FASTQ files, detect single-end vs paired-end, note experiment type
[ ] 1. Verify tools are installed (FastQC, MultiQC, Trim Galore + Cutadapt) — install if missing
[ ] 2. Run FastQC on raw reads (multi-threaded)
[ ] 3. Parse and interpret each module; flag any WARN/FAIL with severity
[ ] 4. Decide with the user whether trimming is needed (don't trim reflexively)
[ ] 5. If trimming: run Trim Galore, then re-run FastQC on trimmed reads
[ ] 6. If >1 sample: run MultiQC to aggregate raw (and trimmed) reports
[ ] 7. Summarize findings and recommend next steps
```

Don't blindly execute every step. Steps 4–7 depend on what step 3 reveals and what the user wants.

---

## Step 0: Identify inputs

Before running anything, list the FASTQ files and classify them. This determines how the rest of the workflow runs.

```bash
# Common FASTQ file patterns
ls *.fastq.gz *.fq.gz *.fastq *.fq 2>/dev/null
```

For each file or sample, capture:

- **Paired-end vs single-end.** Paired-end reads come in matched pairs, conventionally named `*_R1.fastq.gz` / `*_R2.fastq.gz` or `*_1.fq.gz` / `*_2.fq.gz`. If the user only provides one file per sample, treat as single-end. If naming is ambiguous, ask.
- **Experiment type** (ChIP-seq, ATAC-seq, RNA-seq, WGS/WES, other). This changes how some FastQC modules are interpreted — for example, K-mer FAILs and over-representation FAILs are *expected* in ChIP-seq immunoprecipitation samples but suspicious in RNA-seq. Ask if not stated.
- **Compression.** Both gzipped (`.gz`) and uncompressed work with all the tools used here. No need to decompress upfront.

If file paths are quoted with spaces or live on a shared mount, expand and verify they exist with `ls -lh` before passing to tools.

---

## Step 1: Verify tools

The skill depends on four executables: `fastqc`, `multiqc`, `trim_galore`, and `cutadapt`. Check first; install only what's missing.

```bash
for t in fastqc multiqc trim_galore cutadapt; do
  command -v $t >/dev/null 2>&1 && echo "$t: $(command -v $t)" || echo "$t: MISSING"
done
```

If anything is missing, read `references/installation.md` for platform-specific install commands (apt, conda/mamba, pip, Homebrew). On most Linux/Mac systems with `pip` and `apt`/`brew`, this works:

```bash
# FastQC (Java-based) — apt on Debian/Ubuntu, brew on macOS
sudo apt-get install -y fastqc        # Debian/Ubuntu
# brew install fastqc                 # macOS

# Python tools — MultiQC, Cutadapt
pip install --user multiqc cutadapt

# Trim Galore — small Perl wrapper around Cutadapt
# Download the latest from https://github.com/FelixKrueger/TrimGalore/releases
```

Verify versions after install — FastQC ≥0.12, MultiQC ≥1.20, Trim Galore ≥0.6, Cutadapt ≥4.0 are reasonable floors as of 2026.

---

## Step 2: Run FastQC

FastQC produces, for each input FASTQ, an HTML report and a `.zip` archive containing the same plots as static images plus structured text files (`fastqc_data.txt`, `summary.txt`) that downstream tools — and the parser script in this skill — read.

Create an output directory and run FastQC with multi-threading. Each thread handles one file, so `-t N` only helps when you have ≥N input files.

```bash
mkdir -p qc/raw_fastqc

# Pick threads = min(number of files, number of CPU cores). 4 is a safe default.
fastqc -o qc/raw_fastqc -t 4 *.fastq.gz
```

Notes:

- FastQC accepts multiple files and wildcards. No need to loop.
- For very large files, FastQC streams the input, so memory usage stays modest (~250 MB per thread by default; raise with `--memory`).
- BAM/SAM input is also supported, but this skill targets FASTQ.

The HBC tutorial walks through these flags in detail; refer the user there if they want background.

---

## Step 3: Interpret the FastQC report

For each sample, FastQC reports PASS/WARN/FAIL across roughly a dozen modules. **The flags are heuristics, not verdicts.** A WARN or FAIL often reflects a genuine biological signal rather than a problem — over-represented sequences in a ChIP-seq IP sample, K-mer enrichment from binding motifs, GC content shifted by an enriched genomic region. Treat the flags as a checklist of things to look at, then judge in context.

### Quick programmatic interpretation

Use the bundled parser to turn each `*_fastqc.zip` into a structured summary:

```bash
python3 scripts/parse_fastqc.py qc/raw_fastqc/
```

It prints a per-sample table of module statuses, basic statistics (total reads, %GC, read length, %duplication), and a list of plain-English flags ranked by severity. Feed this output back to the user before recommending action.

### What each module means

The detail belongs in a reference, not here. Read `references/interpretation.md` for:

- Module-by-module description of what's measured and what good vs. bad looks like
- Context-specific notes for ChIP-seq, ATAC-seq, and RNA-seq (when a FAIL is expected vs. concerning)
- Common causes for each failure mode and what to do about them

The quick rules of thumb worth keeping in your head:

| Module                        | When to worry                                                                |
| ----------------------------- | ---------------------------------------------------------------------------- |
| Per base sequence quality     | Quality drops at the **start** or **middle**, not just the end               |
| Per sequence quality scores   | Bimodal distribution or a large peak below Q20                               |
| Per base sequence content     | Persistent imbalance past the first ~10–12 bp (early bias is normal)         |
| Per sequence GC content       | Multi-modal or sharply shifted vs. expected — suggests contamination         |
| Sequence length distribution  | Unexpected variation when the sequencer should produce uniform length        |
| Sequence duplication levels   | Very high in low-input or amplicon-free libraries (high in ChIP IP is normal)|
| Over-represented sequences    | Adapter sequences listed (expected in ChIP IP, but flag-worthy elsewhere)    |
| Adapter content               | Any non-trivial adapter percentage — strong signal to trim                   |
| K-mer content                 | FAIL is expected in ChIP-seq IP; suspicious in RNA-seq                       |

---

## Step 4: Decide whether to trim

Trimming has costs (shorter reads, lost data, runtime) and isn't always needed. Recommend trimming when at least one of these holds:

- **Adapter content** module is WARN/FAIL.
- **Per base sequence quality** drops below Q20 by the end of the read, in a way that would hurt alignment.
- **Over-represented sequences** include adapter-like sequences.
- The library is small-RNA or amplicon-based (where adapter readthrough is expected).

Recommend *not* trimming when the data looks clean and the downstream aligner (e.g., STAR, BWA-MEM, Bowtie2) is end-to-end soft-clipping tolerant — modern aligners handle some adapter contamination fine.

Present the recommendation to the user with a brief reason and ask before trimming. Don't trim silently.

---

## Step 5: Trim with Trim Galore

Trim Galore wraps Cutadapt with sensible defaults: auto-detect the adapter, trim with Q20 quality cutoff, drop reads shorter than 20 bp after trimming, and run FastQC on the trimmed output. It handles single-end and paired-end automatically.

```bash
mkdir -p qc/trimmed

# Single-end
trim_galore -o qc/trimmed --fastqc sample.fastq.gz

# Paired-end (order matters: R1 first, R2 second)
trim_galore -o qc/trimmed --fastqc --paired sample_R1.fastq.gz sample_R2.fastq.gz
```

Use the wrapper script for multiple samples or paired-end batches:

```bash
bash scripts/trim_reads.sh -i raw/ -o qc/trimmed/ --paired
```

Trim Galore outputs `*_trimmed.fq.gz` (SE) or `*_val_1.fq.gz` / `*_val_2.fq.gz` (PE) plus per-file trimming reports. With `--fastqc`, it also generates the post-trimming FastQC reports — no need to re-run them manually.

Re-inspect the post-trim FastQC: the adapter content module should be PASS, and the per-base quality should hold above Q20 across the read length. If the same WARN/FAIL persists, something other than adapters or quality is driving it.

### When to choose fastp instead

`fastp` is a faster alternative that does QC, trimming, and reporting in a single pass. It's a reasonable choice for very large datasets where Trim Galore's per-file overhead matters. Trim Galore is preferred when matching the HBC workflow; fastp when speed is the constraint.

---

## Step 6: Aggregate with MultiQC

For more than one sample, MultiQC compiles a single interactive HTML report from all the FastQC and Trim Galore outputs in a directory tree.

```bash
# Run from the project root; MultiQC recursively finds tool outputs
multiqc qc/ -o qc/multiqc_report --title "Sample QC summary"
```

MultiQC auto-detects FastQC, Trim Galore, Cutadapt, and many other tool outputs. The resulting `multiqc_report.html` is a single file that opens in any browser and is the right artifact to share with collaborators.

---

## Step 7: Summarize and recommend

After running the pipeline, give the user a short, structured summary:

- **Samples processed** — counts and types
- **Overall quality** — one-line verdict per sample
- **Issues flagged** — module name, severity, plain-English explanation, and what (if anything) was done about it
- **Files produced** — paths to the HTML reports they should open
- **Next steps** — typically alignment, with any caveats (e.g., "Sample X has elevated duplication; consider deduplication after alignment.")

Keep this short. The reports are the artifact; the summary is a navigation aid.

---

## Reference files

- `references/interpretation.md` — Module-by-module FastQC interpretation with ChIP/ATAC/RNA-seq context. Read before commenting on a specific module.
- `references/installation.md` — Install instructions for FastQC, MultiQC, Trim Galore, Cutadapt on Linux, macOS, and via conda/mamba.
- `references/fastq-format.md` — FASTQ format primer (the 4-line record, Phred scoring, encoding offsets). Useful when explaining what a quality score means or debugging a malformed file.

## Bundled scripts

- `scripts/run_fastqc.sh` — Thin wrapper that picks a sensible thread count and creates the output directory.
- `scripts/parse_fastqc.py` — Reads `*_fastqc.zip` archives and prints a structured per-sample summary with severity-ranked flags. Use this before writing the user-facing interpretation.
- `scripts/trim_reads.sh` — Trim Galore wrapper for batches of single-end or paired-end files.
- `scripts/run_multiqc.sh` — MultiQC wrapper with sensible defaults.
