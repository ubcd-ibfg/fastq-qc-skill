# fastq-qc

A Claude skill for quality-controlling FASTQ sequencing reads.

Wraps **FastQC**, **Trim Galore**, and **MultiQC** behind a single conversational workflow: Claude runs QC, parses the reports into structured findings, recommends whether trimming is needed, and aggregates multi-sample results. Interpretation guidance follows the [Harvard Chan Bioinformatics Core ChIP-seq tutorial](https://hbctraining.github.io/Investigating-chromatin-biology-ChIPseq/lessons/03_QC_FASTQC.html), with assay-specific notes for ChIP-seq, ATAC-seq, and RNA-seq.

---

## What's in the box

```
fastq-qc/
├── SKILL.md                      7-step workflow Claude follows end-to-end
├── references/
│   ├── interpretation.md         Per-module field guide (≈12 FastQC modules,
│   │                             what good/bad looks like, assay context)
│   ├── installation.md           Install paths for conda/apt/brew/pip
│   └── fastq-format.md           FASTQ format + Phred encoding primer
└── scripts/
    ├── run_fastqc.sh             FastQC wrapper, auto-picks thread count
    ├── trim_reads.sh             Trim Galore wrapper, handles SE & PE batches
    ├── run_multiqc.sh            MultiQC aggregation wrapper
    └── parse_fastqc.py           Parses *_fastqc.zip → structured per-sample
                                  findings (text / JSON / CSV)
```

The skill itself depends on four command-line tools — **FastQC**, **MultiQC**, **Trim Galore**, and **Cutadapt** — which the skill checks for and helps install on first run. See `fastq-qc/references/installation.md` for platform-specific install commands (conda is recommended).

---

## Installation

Skills are folders containing a `SKILL.md` file plus optional `scripts/` and `references/`. Where you put that folder depends on which Claude product you use.

### Claude.ai (web, desktop, mobile)

Skills are available on Free, Pro, Max, Team, and Enterprise plans and require code execution to be enabled.

1. **Enable code execution and skills.** Settings → Capabilities → toggle on *Code execution and file creation*. Team / Enterprise users may need an organization owner to enable both *Code execution* and *Skills* in Organization settings first.
2. **Open the skill manager.** Customize → Skills.
3. **Upload the skill.** Click "Upload skill" and select [`dist/fastq-qc.skill`](dist/fastq-qc.skill) from this repo. (`.skill` is a zip — Claude.ai unpacks it for you.)
4. **Toggle it on** in the skills list. Claude will load it automatically when a FASTQ-related task comes up.

Anthropic's docs: [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

### Claude Code (terminal)

Skills live in `~/.claude/skills/` (personal, available in every project) or `.claude/skills/` (project-scoped, lives with the repo).

**Personal install:**

```bash
git clone https://github.com/<your-user>/fastq-qc-skill.git
cp -r fastq-qc-skill/fastq-qc ~/.claude/skills/
```

**Project install** (the skill ships with a specific repo and is shared with collaborators):

```bash
git clone https://github.com/<your-user>/fastq-qc-skill.git
cp -r fastq-qc-skill/fastq-qc /path/to/your/project/.claude/skills/
```

Claude Code watches both directories and picks up the new skill within the current session — no restart needed. Verify it loaded by running `/skills` in any Claude Code session; `fastq-qc` should appear.

Anthropic's docs: [Extend Claude with skills](https://code.claude.com/docs/en/skills).

### Claude Code in VS Code, JetBrains, or other IDEs

The IDE extensions reuse the same skill directories as the terminal client. If you've already installed for the terminal, the IDE will see it. Otherwise, follow the Claude Code instructions above and restart your IDE.

### Claude API

Skills are available in beta for API users via the code execution tool. See the [Skills API Quickstart](https://docs.claude.com/en/api/overview) for the current upload and reference flow.

### Direct download (no git)

If you'd rather not clone, grab the packaged `.skill` zip from `dist/fastq-qc.skill` or download a release archive from GitHub, unzip it, and copy the `fastq-qc/` folder into your skills directory.

---

## What Claude does when the skill triggers

The skill activates whenever your prompt involves FASTQ files, sequencing read quality, FastQC, MultiQC, adapter trimming, or raw NGS data — you don't need to invoke it by name.

The 7-step workflow Claude follows:

1. **Identify inputs.** List FASTQ files, detect single-end vs paired-end pairing, ask about assay type (ChIP-seq, RNA-seq, ATAC-seq, etc.) if not stated.
2. **Verify tool availability.** Check `fastqc`, `multiqc`, `trim_galore`, `cutadapt`; offer to install anything missing.
3. **Run FastQC** on the raw reads (multi-threaded, sensible defaults).
4. **Interpret each module.** Uses `parse_fastqc.py` to extract structured findings from the FastQC zip, ranks WARN/FAIL flags by severity, and translates each one into plain English with assay-specific context (e.g., "high duplication is expected in ChIP-seq IP samples").
5. **Recommend trimming or not** based on the findings (and ask before acting).
6. **Trim with Trim Galore** if needed, then re-run FastQC on the trimmed reads.
7. **Aggregate with MultiQC** if more than one sample, and produce a final summary with paths to the artifacts.

The interpretation framework is module-by-module guidance based on the HBC tutorial. Claude won't reflexively recommend trimming on every WARN — many WARN/FAIL flags are biologically expected (random-hexamer priming bias in RNA-seq, K-mer enrichment in ChIP-seq, etc.) and the skill knows the difference.

---

## Example usage

### Example 1 — single sample, basic QC

> **Prompt:** *I just got the FASTQ back from the sequencer, it's at `~/data/sample_A.fastq.gz`. Can you check quality?*

**What Claude does:**
- Verifies FastQC is installed.
- Runs FastQC on `sample_A.fastq.gz` with multi-threading.
- Parses the resulting zip into a structured summary.
- Reports something like:

```
Sample: sample_A
  Total reads: 12,438,201
  Read length: 75
  %GC: 42
  Approx. duplication: 18.4%

  Flags (1):
    [WARN] Adapter Content
      Some adapter contamination detected. Trimming recommended.

  Verdict: Mostly clean — quality and GC look fine.
  Single WARN on adapter content. Want me to trim with Trim Galore
  before alignment?
```

### Example 2 — paired-end batch with RNA-seq context

> **Prompt:** *Run QC on the RNA-seq paired-end FASTQs in `/data/run42/raw/`. Trim if anything is off and give me one combined report at the end.*

**What Claude does:**
- Detects 12 files (6 R1/R2 pairs) and confirms the pairing.
- Runs FastQC on all 12 raw files in parallel.
- Notes that several samples have a FAIL on *Per base sequence content* — flags this as **expected for random-hexamer-primed RNA-seq** (first ~12 bp bias) and does **not** recommend trimming for that reason alone.
- Spots adapter contamination on 3 samples and runs Trim Galore in paired-end mode on those.
- Runs MultiQC across both raw and trimmed reports.
- Produces:

```
qc/
├── raw_fastqc/               (12 FastQC reports — pre-trim)
├── trimmed/                  (trimmed FASTQs + post-trim FastQC)
└── multiqc/run42_multiqc_report.html   ← one HTML to share
```

[`examples/example_multiqc_report.html`](examples/example_multiqc_report.html) shows a real MultiQC report this skill produced on a 4-sample paired-end test set. Open it in a browser to see what the final artifact looks like.

### Example 3 — interpreting a "scary" FastQC report

> **Prompt:** *I ran FastQC on my ChIP-seq IP samples and it's a sea of red FAILs — over-represented sequences, K-mer content, duplication, everything. Should I be worried?*

**What Claude does:**
- Reads the existing FastQC zips with the parser (no need to re-run).
- Cross-references each FAIL against the assay type (ChIP-seq IP).
- Reports:

```
Most of what you're seeing is expected for a ChIP-seq IP sample, not a problem:

  Over-represented sequences (FAIL)  → Expected. You're enriching for
                                       protein-bound regions; over-representation
                                       is the point of the experiment.
  K-mer content (FAIL)               → Expected. Binding motifs of the IP'd
                                       factor appear as enriched K-mers. The HBC
                                       tutorial explicitly calls a K-mer FAIL "a
                                       sign of good signal in your data."
  Sequence duplication (FAIL)        → Expected for ChIP-seq IP. Handle after
                                       alignment with MarkDuplicates, not at the
                                       FASTQ stage.

The flag actually worth looking at:

  Per-base sequence quality (WARN)   → Quality dips below Q20 in the last 10 bp
                                       of the read. Worth quality-trimming before
                                       alignment.

Want me to run Trim Galore at Q20 to clean up the read tails?
```

This is the value the skill adds: it doesn't just *run* the tools — it knows which red flags mean something and which are noise.

### Example 4 — one-off question about a single FASTQ

> **Prompt:** *What does Phred quality 33 mean and how is that different from Phred 64?*

**What Claude does:**
- Loads `references/fastq-format.md` for the encoding details.
- Explains the offset (+33 = Sanger / Illumina 1.8+, +64 = legacy Illumina 1.3–1.7), the ASCII table mapping, and that all modern data is +33.

The skill is happy to answer reference questions without running anything.

---

## Sample outputs in this repo

- [`examples/example_multiqc_report.html`](examples/example_multiqc_report.html) — interactive multi-sample QC report produced from 4 RNA-seq paired-end FASTQs (yeast, ~50k reads each, from the nf-core test dataset). Open in any browser.
- [`examples/example_qc_summary.csv`](examples/example_qc_summary.csv) — the CSV summary `parse_fastqc.py --csv` produced from the same run.

---

## Security note

This skill bundles shell and Python scripts that Claude can execute, and it will offer to install FastQC, MultiQC, Trim Galore, and Cutadapt (via `apt`, `pip`, or `conda`) if they're missing. All four are well-known open-source bioinformatics tools — but review the scripts before installing if you're in a regulated environment, and inspect what package manager commands Claude runs before approving them. Anthropic's general guidance: only install skills from sources you trust, and read what they bundle.

---

## Acknowledgments

### Source tutorial

The QC interpretation framework in `fastq-qc/references/interpretation.md` is adapted from the [Harvard Chan Bioinformatics Core's FastQC lesson](https://hbctraining.github.io/Investigating-chromatin-biology-ChIPseq/lessons/03_QC_FASTQC.html), part of their *Introduction to ChIP-Seq using high-performance computing* workshop.

> This lesson has been developed by members of the teaching team at the [Harvard Chan Bioinformatics Core (HBC)](http://bioinformatics.sph.harvard.edu/). These are open access materials distributed under the terms of the [Creative Commons Attribution license](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0), which permits unrestricted use, distribution, and reproduction in any medium, provided the original author and source are credited.

Reading the original tutorial is still the best way to learn FastQC by hand — it covers running FastQC on an HPC cluster via LMOD modules, transferring reports with FileZilla, and walks through the same report screenshots this skill's interpretation guide is built around.

### Tools wrapped by this skill

- **[Babraham Bioinformatics](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/)** — authors of FastQC.
- **[Felix Krueger](https://github.com/FelixKrueger/TrimGalore)** — Trim Galore.
- **[MultiQC](https://multiqc.info/)** — Phil Ewels et al.
- **[Cutadapt](https://cutadapt.readthedocs.io/)** — Marcel Martin.

This skill is community-built and not affiliated with Anthropic, the Harvard Chan Bioinformatics Core, or the tool authors.

## License

MIT — see [LICENSE](LICENSE). The HBC tutorial content the interpretation guidance is derived from is CC BY 4.0; attribution above.
