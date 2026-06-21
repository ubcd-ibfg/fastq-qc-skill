# Example outputs

Real artifacts produced by the `fastq-qc` skill on a small test dataset, so you can see what to expect before installing.

## Test input

Four paired-end RNA-seq FASTQ files from the [nf-core test datasets](https://github.com/nf-core/test-datasets/tree/rnaseq/testdata) (yeast, *Saccharomyces cerevisiae*, ~50,000 reads per file):

- `sample1_R1.fastq.gz` + `sample1_R2.fastq.gz` (SRR6357070)
- `sample2_R1.fastq.gz` + `sample2_R2.fastq.gz` (SRR6357071)

## Files

### `example_multiqc_report.html`

The MultiQC interactive report aggregating all 12 reports produced by the workflow (4 raw FastQC reports + 4 post-trim FastQC reports + 4 Cutadapt trimming reports). Open it in any browser.

This is what a user typically shares with collaborators — a single self-contained HTML that opens locally with no server, no installation.

### `example_qc_summary.csv`

The per-sample summary CSV that `scripts/parse_fastqc.py --csv` produces. Columns:

- `sample` — sample name (FASTQ basename minus extension)
- `total_reads` — total read count from FastQC's Basic Statistics
- `read_length` — read length or range
- `pct_gc` — overall %GC content
- `approx_dup_pct` — approximate duplication percentage (100 − FastQC's deduplicated percentage)
- `num_warn`, `num_fail` — count of modules in each status
- `flagged_modules` — semicolon-separated list of modules that WARN'd or FAIL'd

Useful for dropping into a spreadsheet or LIMS, or for spot-checking many samples at once without opening every HTML.

## Reproducing these outputs

```bash
# Download the same test data (you'll need curl)
mkdir -p raw
for srr in SRR6357070 SRR6357071; do
  for r in 1 2; do
    curl -fsSL -o raw/${srr}_${r}.fastq.gz \
      https://raw.githubusercontent.com/nf-core/test-datasets/rnaseq/testdata/GSE110004/${srr}_${r}.fastq.gz
  done
done

# Then ask Claude (with the skill installed):
# "Run paired-end QC on the FASTQs in raw/, trim if needed, aggregate with MultiQC."
```

The skill will produce a similar `qc/multiqc/*_multiqc_report.html` to the one in this folder.
