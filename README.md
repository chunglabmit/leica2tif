# LEICA2TIF convert .lif files to TIFF

## Installation

This package is pip installable, but can most easily be
installed using Anaconda, e.g.:

```bash
wget https://raw.githubusercontent.com/chunglabmit/leica2tif/master/environment.yaml
conda env create -f environment.yaml
```

## Usage

```bash
leica2tif \
  --input <lif-file> \
  --output-pattern <output-pattern> \
  [--series <series>] \
  [--z-min <z-min>] \
  [--z-max <z-max>] \
  [--c <channel>] \
  [--t-min <t-min>] \
  [--t-max <t-max>] \
  [--compression <compression]
```
where
* **lif-file** is the path to the Leica file.
* **output-pattern** is a *format* style file naming pattern, e.g.
  `/path-to/img_{z:04d}-{c:04d}-{t:04d}.tiff`. Substitutions are made
  for z, c (the channel #) and t (the time as an index).
* **series** the zero-based series # to be read out of the .lif file.
  A quick trick here is to open the .lif in Fiji and subtract 1
  from the series you want.
* **z-min** read z frames starting at this z (default 0).
* **z-max** read z frames up until this z (default all z).
* **c** read this channel index (starting at zero). This may be
  specified multiple times. Default is to read all channels.
* **t-min** read time frames starting at this t (default 0).
* **t-max** read time frames up until this t.
* **compression** compression level (0-9) for tiffs, defaults to 3.