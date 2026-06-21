# FastQC module interpretation

A field guide to reading a FastQC report. Each module section covers what's measured, what good looks like, what bad looks like, and how interpretation shifts across assay types (ChIP-seq, ATAC-seq, RNA-seq). Based on the [HBC ChIP-seq tutorial](https://hbctraining.github.io/Investigating-chromatin-biology-ChIPseq/lessons/03_QC_FASTQC.html) and the [official FastQC documentation](http://www.bioinformatics.babraham.ac.uk/projects/fastqc/Help/).

The most important framing: **PASS/WARN/FAIL are heuristics, not verdicts.** FastQC compares each sample against expectations for a "normal" random library. Real experiments routinely violate those expectations for good biological reasons. A FAIL is a prompt to think, not a problem to fix.

## Contents

1. [Basic Statistics](#basic-statistics)
2. [Per base sequence quality](#per-base-sequence-quality)
3. [Per tile sequence quality](#per-tile-sequence-quality)
4. [Per sequence quality scores](#per-sequence-quality-scores)
5. [Per base sequence content](#per-base-sequence-content)
6. [Per sequence GC content](#per-sequence-gc-content)
7. [Per base N content](#per-base-n-content)
8. [Sequence length distribution](#sequence-length-distribution)
9. [Sequence duplication levels](#sequence-duplication-levels)
10. [Overrepresented sequences](#overrepresented-sequences)
11. [Adapter content](#adapter-content)
12. [K-mer content](#k-mer-content)

---

## Basic Statistics

**What it shows:** Total reads, sequence length, %GC, encoding.

**Read first.** Confirm:

- **Total reads** match the order placed with the sequencing facility. Order-of-magnitude mismatches mean missing files or a bad demultiplex.
- **Sequence length** matches the kit (e.g., 50, 75, 100, 150 bp). A range when the kit is uniform-length suggests upstream trimming already happened.
- **%GC** is in the expected range for the organism — ~41% for human, ~42% for mouse, ~38% for *S. cerevisiae*. A large deviation signals contamination or an enriched genomic region.
- **Encoding** is Sanger / Illumina 1.9 (Phred+33). Anything else (Illumina 1.3/1.5, Phred+64) means old data — most tools assume Phred+33.

## Per base sequence quality

**What it shows:** Box-and-whisker of quality scores at each base position. The green / yellow / red bands mark good / mediocre / poor regions.

**Good:** Most boxes sit in the green band (Q≥28) across the read. A gentle drop at the 3′ end is normal — Illumina chemistry loses signal late in the run.

**Bad:**

- Drop at the **5′ end** — unusual; could indicate a problem with the first few cycles of the run. Trim the affected bases.
- Drop in the **middle** of the read — call the sequencing facility. This shouldn't happen.
- Median quality below Q20 by the 3′ end — quality-trim before alignment.

**Assay-specific:** No major differences. This module is interpreted the same way for all NGS assays.

## Per tile sequence quality

**What it shows:** Heatmap of quality deviation across flowcell tiles (Illumina only).

**Good:** Uniformly blue. Quality consistent across tiles.

**Bad:** Streaks of red/orange on specific tiles indicate transient issues — a bubble in the flowcell, debris, a smudge. If contained to a few tiles, the affected reads can be filtered. If widespread, contact the facility.

**Assay-specific:** None.

## Per sequence quality scores

**What it shows:** Distribution of mean quality across reads.

**Good:** A single sharp peak at high quality (Q≥35 typical for modern instruments).

**Bad:**

- Bimodal distribution — a subset of reads is systematically low-quality, often the second read in a paired-end library if R2 has degraded.
- Large left tail — a meaningful fraction of reads are below the threshold for reliable alignment.

**Assay-specific:** None.

## Per base sequence content

**What it shows:** Percentage of A/T/G/C at each base position. In a random library, the four lines should be roughly parallel and reflect the organism's overall composition.

**Good for whole-genome / WGS / WES:** Lines parallel and stable across the read.

**Expected biases (don't worry):**

- **First ~10–12 bp** are non-random for **RNA-seq with random hexamer priming** — the hexamers aren't actually random. FastQC will FAIL this module on most RNA-seq libraries, and that's fine.
- **Bisulfite (methylation) libraries** show strong base composition bias by design.
- **Targeted amplicon** and **small-RNA** libraries show strong bias from the conserved primer/adapter.

**Concerning:**

- Persistent imbalance across the **whole read**, not just the start — indicates a real contamination or library construction issue.
- Sharp jumps mid-read — often adapter readthrough.

**Assay-specific:**

- **RNA-seq:** Expect early bias from random hexamer priming. WARN/FAIL is the norm.
- **ChIP-seq, ATAC-seq:** Expect roughly uniform composition; early bias suggests something off.

## Per sequence GC content

**What it shows:** Distribution of mean GC content across reads vs. a theoretical normal distribution at the same mean.

**Good:** A single peak at the organism's expected GC.

**Bad:**

- **Bimodal** distribution — almost always contamination. The second peak is the contaminant's GC. Run a contamination screen (e.g., FastQ Screen, Kraken2).
- **Shifted peak** — wrong organism, mislabeled sample, or strong enrichment of an unusual genomic region.
- **Broad peak** — adapter dimers or low-complexity content stretching the distribution.

**Assay-specific:**

- **ChIP-seq IP samples:** A slight shift from input is possible if the bound regions have unusual GC. Compare IP vs. input.
- **Amplicon / 16S:** A sharp single peak at the amplicon's GC is expected — looks "abnormal" vs. a random library but is correct.

## Per base N content

**What it shows:** Percentage of `N` (no-call) bases at each position.

**Good:** Below 1% everywhere.

**Bad:** Any sustained spike above a few percent indicates the sequencer failed to make a confident call. A spike at one position can sometimes be fixed by hard-trimming that position.

**Assay-specific:** None.

## Sequence length distribution

**What it shows:** Histogram of read lengths in the file.

**Good for raw Illumina output:** A single value (e.g., all reads = 50 bp). FastQC sometimes WARNs even on uniform-length data — ignore the WARN if the histogram is one bar.

**Expected variation:**

- **Already-trimmed reads** (post Trim Galore / fastp) — variable length is the *point*.
- **Long-read platforms (PacBio, Nanopore)** — broad distribution by nature.
- **Small-RNA libraries** — distribution peaks at the miRNA size (~22 nt).

**Concerning:** Unexpected variation on a raw fixed-length Illumina run — usually means adapter trimming happened upstream and wasn't communicated.

**Assay-specific:** As above. The HBC tutorial notes that variable lengths in ChIP-seq raw data can indicate adapter contamination that was partially cleaned upstream.

## Sequence duplication levels

**What it shows:** Estimated fraction of reads that are exact duplicates, broken down by duplication level.

**Good for unbiased libraries:** Low duplication (<20% in the first bin is fine).

**Expected high duplication (not alarming):**

- **ChIP-seq IP samples** — enriching for specific regions means the same fragment can be sequenced many times. Duplicates are typically removed *after* alignment, not at the FASTQ stage. Don't deduplicate reads before mapping.
- **Amplicon / targeted panels** — by design, the same loci are over-represented.
- **Low-input libraries** (e.g., ATAC-seq from few cells) — PCR amplification cycles compound duplicates.
- **Deep sequencing** — at very high depth, duplicates become statistically inevitable.

**Concerning:** High duplication in a deep, unbiased (e.g., WGS) library implies low library complexity — sequencing more reads will mostly resequence the same molecules.

**Assay-specific:**

- **ChIP-seq:** WARN/FAIL is expected, especially for sharp-peak factors. Handle after alignment with Picard MarkDuplicates or `samtools markdup`.
- **ATAC-seq:** Some duplication is expected from low input; very high duplication suggests over-amplification.
- **RNA-seq:** High duplication in highly-expressed transcripts is normal; check that it's not uniform across the library.

## Overrepresented sequences

**What it shows:** Sequences that appear in >0.1% of reads, with a guess at their source.

**Good:** Empty or near-empty list.

**Bad:**

- Adapter sequences — trim.
- rRNA — RNA-seq with failed rRNA depletion.
- PCR primers — usually fine if expected; trim if not.
- "No Hit" sequences in high abundance — possible novel contaminant; BLAST them.

**Assay-specific:**

- **ChIP-seq IP:** Over-represented sequences from the binding motif are *expected and good*. Lack of over-representation in IP doesn't mean failure but is worth noting.
- **ChIP-seq input control:** Should have few over-represented sequences. If it does, suspect protocol-specific bias.
- **Small-RNA:** Over-representation of mature miRNAs is the goal.
- **Amplicon:** Over-representation of the target sequence is the goal.

## Adapter content

**What it shows:** Cumulative percentage of reads showing each known adapter sequence at each position. FastQC checks for Illumina Universal Adapter, Illumina Small RNA, Nextera, and a few others.

**Good:** All lines stay near 0%.

**Bad:** Any line rising above a few percent — adapter readthrough is happening. The crossover point tells you the insert size distribution.

This is **the most actionable QC module** — adapter contamination has a clear fix (trim it), and aligners do varying amounts of soft-clipping but trimming up front is cleaner.

**Assay-specific:** Identifies which adapter to use for trimming. Trim Galore's auto-detection usually gets this right, but if it doesn't, this module tells you what to specify with `--adapter`.

## K-mer content

**What it shows:** 7-mers with positionally biased enrichment, plotted as percentage of reads at each position.

**Good for whole-genome:** No enriched K-mers.

**Expected K-mer enrichment (not alarming):**

- **ChIP-seq IP** — binding motifs of the IP'd factor show up as enriched K-mers. The HBC tutorial calls this out specifically: "a FAIL of this metric is expected and is actually a sign of good signal in your data." Concentrated K-mers at the read start are particularly motif-suggestive.
- **Adapter contamination** — adapter sequences enrich as K-mers.
- **Repeat-heavy regions** — telomeric or centromeric reads enrich for their characteristic K-mers.

**Concerning:**

- K-mer FAIL in RNA-seq or input ChIP — investigate.
- K-mer enrichment matching an adapter — trim.

**Assay-specific:**

- **ChIP-seq IP:** FAIL is good news.
- **ChIP-seq input:** FAIL suggests protocol bias.
- **ATAC-seq:** No enrichment expected — like input ChIP.
- **RNA-seq:** No enrichment expected except from rRNA contamination or adapter.

---

## How to phrase findings to the user

When summarizing, lead with the verdict, then the evidence, then the action.

**Good:** "Sample S1 looks clean. All modules PASS except a WARN on Per base sequence content from the first 10 bp — standard for random-hexamer-primed RNA-seq. No action needed."

**Less good:** "Sample S1 has a Per base sequence content WARN. The per-base sequence content module shows that..."

The first version lets the user act; the second makes them parse jargon to extract the same conclusion.
