# Installing FastQC, MultiQC, Trim Galore, and Cutadapt

Check what's already available before installing:

```bash
for t in fastqc multiqc trim_galore cutadapt; do
  command -v $t >/dev/null 2>&1 && echo "$t: $(command -v $t) ($($t --version 2>&1 | head -1))" || echo "$t: MISSING"
done
```

If a tool is missing, use the platform-appropriate route below.

## Recommended: conda / mamba (cross-platform)

The cleanest install is via the `bioconda` channel. Use `mamba` if available (faster solver); otherwise plain `conda`.

```bash
# One environment, all four tools
mamba create -n qc -c bioconda -c conda-forge \
  fastqc multiqc trim-galore cutadapt
mamba activate qc
```

This works identically on Linux and macOS. Versions in bioconda are kept current.

## Debian / Ubuntu (apt + pip)

```bash
# FastQC and Trim Galore are packaged in the official repos
sudo apt-get update
sudo apt-get install -y fastqc trim-galore

# MultiQC and Cutadapt via pip
pip install --user multiqc cutadapt
```

The apt versions of FastQC and Trim Galore lag behind upstream. If you need the latest, install Trim Galore from GitHub releases (see below) and FastQC from the Babraham download.

## macOS (Homebrew + pip)

```bash
brew install fastqc cutadapt
pip install --user multiqc

# Trim Galore from GitHub (no Homebrew formula)
curl -fsSL https://github.com/FelixKrueger/TrimGalore/archive/refs/tags/0.6.10.tar.gz | tar xz
sudo mv TrimGalore-0.6.10/trim_galore /usr/local/bin/
```

## Manual install (when package managers aren't an option)

### FastQC

Java-based. Requires Java ≥11.

```bash
wget https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.12.1.zip
unzip fastqc_v0.12.1.zip
chmod +x FastQC/fastqc
sudo ln -s "$PWD/FastQC/fastqc" /usr/local/bin/fastqc
```

### Trim Galore

Perl wrapper. Requires Perl ≥5 (standard on Linux/Mac).

```bash
curl -fsSL https://github.com/FelixKrueger/TrimGalore/archive/refs/tags/0.6.10.tar.gz | tar xz
sudo ln -s "$PWD/TrimGalore-0.6.10/trim_galore" /usr/local/bin/trim_galore
```

### MultiQC and Cutadapt

Python packages. Use a venv or `--user` to avoid conflicts.

```bash
python3 -m pip install --user multiqc cutadapt
# Make sure ~/.local/bin is on PATH:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

## HPC / module systems (LMOD)

On many academic clusters the tools are pre-installed. Check first:

```bash
module avail fastqc
module avail multiqc
module avail trim_galore
module spider trim_galore  # for cross-version info
```

Load with `module load fastqc/0.12.1` (or whatever version is available). On O2 (Harvard), this matches the HBC tutorial workflow.

## Verifying the install

```bash
fastqc --version       # FastQC v0.12.1
multiqc --version      # multiqc, version 1.20
trim_galore --version  # Quality-/Adapter-/RRBS-/Speciality-Trimming
cutadapt --version     # 4.6
```

If any of these fail, the tool isn't on `PATH`. Common fixes: re-source `~/.bashrc`, add `$HOME/.local/bin` to `PATH`, or activate the conda environment.
