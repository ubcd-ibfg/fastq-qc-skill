# FASTQ format reference

Background for when you need to explain what's in a FASTQ file, debug a malformed one, or interpret a quality score.

## The 4-line record

Every read in a FASTQ file occupies exactly 4 lines:

```
@HWI-ST330:304:H045HADXX:1:1101:1111:61397
CACTTGTAAGGGCAGGCCCCCTTCACCCTCCCGCTCCTGGGGGANNNNNNNNNNANNNCGAGGCCCTGGGGTAGAGGGNNNNNNNNNNNNNNGATCTTGG
+
@?@DDDDDDHHH?GH:?FCBGGB@C?DBEGIIIIAEF;FCGGI#########################################################
```

| Line | Starts with | Contents                                                                  |
| ---- | ----------- | ------------------------------------------------------------------------- |
| 1    | `@`         | Read identifier and optional description (instrument, lane, coordinates)  |
| 2    | A/C/G/T/N   | The nucleotide sequence                                                   |
| 3    | `+`         | Separator; may repeat the identifier from line 1 (most tools ignore this) |
| 4    | (any ASCII) | Quality scores, **same number of characters as line 2**                   |

Line 4 must be the same length as line 2. If it isn't, the file is corrupt — most tools will error out, but some silently produce garbage. `seqkit stats` or `fastqc` will flag this.

## Phred quality scores

Each character on line 4 encodes the Phred quality score for the corresponding base. The score is the logarithmic probability that the base call is wrong:

```
Q = -10 × log10(P)
```

| Phred score | Error probability | Base-call accuracy |
| ----------- | ----------------- | ------------------ |
| 10          | 1 in 10           | 90%                |
| 20          | 1 in 100          | 99%                |
| 30          | 1 in 1,000        | 99.9%              |
| 40          | 1 in 10,000       | 99.99%             |
| 50          | 1 in 100,000      | 99.999%            |
| 60          | 1 in 1,000,000    | 99.9999%           |

Practical thresholds: Q20 is the floor for usable bases; Q30 is the typical target for short-read Illumina data.

## Quality encoding

The Phred score is encoded as a single ASCII character. There are two main encoding offsets:

**Phred+33 (Sanger / Illumina 1.8+).** Used by all modern data.

```
ASCII char:    !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJ
Phred score:   0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
               0         1         2         3         4
```

So `!` = Q0, `5` = Q20, `?` = Q30, `I` = Q40.

**Phred+64 (Illumina 1.3–1.7, Solexa).** Only seen in legacy data. The first usable character is `@` = Q0.

FastQC auto-detects the encoding. Most other tools assume Phred+33. If you have ancient data, convert it once with `seqtk seq -Q64 -V` before doing anything else.

## Paired-end naming conventions

For paired-end runs, each sample has two FASTQ files containing matched reads. Common naming patterns:

- `sample_R1.fastq.gz` / `sample_R2.fastq.gz` (Illumina convention)
- `sample_1.fq.gz` / `sample_2.fq.gz` (SRA / ENA convention)
- `sample.r1.fastq.gz` / `sample.r2.fastq.gz` (occasional)

The two files must have the same number of reads in the same order. Tools that operate on paired-end data (Trim Galore, BWA-MEM, STAR) take both files together. If one of the pair is missing or shorter, alignment will fail at the synchronization step.

## File compression

FASTQ files are almost always gzipped (`.fastq.gz` / `.fq.gz`). FastQC, MultiQC, Trim Galore, and Cutadapt all read gzipped input directly — don't decompress before running them. Decompression doubles disk usage and helps nothing.

To peek at a gzipped FASTQ without fully decompressing:

```bash
zcat sample.fastq.gz | head -8     # first two reads
zcat sample.fastq.gz | wc -l       # total lines (divide by 4 for read count)
```

## Quick sanity checks for a new FASTQ

```bash
# Read count (line count / 4)
echo "Reads: $(( $(zcat sample.fastq.gz | wc -l) / 4 ))"

# Read length (first read)
zcat sample.fastq.gz | awk 'NR==2 {print length($0); exit}'

# Verify line 4 length matches line 2 length for the first 1000 reads
zcat sample.fastq.gz | head -4000 | awk 'NR%4==2 {s=length($0)} NR%4==0 {if (length($0)!=s) print "MISMATCH at read " (NR/4)}'
```

If any of these is unexpected, stop and investigate before running QC tools that assume the file is well-formed.
