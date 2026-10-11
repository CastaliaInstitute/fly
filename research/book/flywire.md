---
title: Ingest and explore FlyWire
kernelspec:
  name: python3
  display_name: Python 3
---

The live FlyWire workflow is local and user-authenticated. The public book build deliberately does not request account tokens or publish raw connectome data.

## Get an official export

The current Codex programmatic-access guidance recommends its static compressed-CSV downloads rather than repeated live queries for bulk analysis. Make a token through your [Codex account](https://codex.flywire.ai/account), keep it in the local environment variable `FLYWIRE_CODEX_TOKEN`, and run `research/download_flywire.py`. The downloader retrieves `connections_princeton` and `consolidated_cell_types`, validates the gzip streams, computes SHA-256 hashes, and writes a local manifest.

```bash
read -s FLYWIRE_CODEX_TOKEN
export FLYWIRE_CODEX_TOKEN
python -m research.download_flywire --dataset fafb --output research/data/raw/fafb-v783
```

Codex requires Google sign-in for exports, and access methods and snapshots can change. The ingestion tool fails clearly if the token is rejected. The tool accepts the FAFB and BANC export identifiers; this research targets adult female FAFB v783 because the memory-circuit literature and annotations are most mature there.

## Prepare the mushroom-body neighborhood

The preparation script finds annotations matching Kenyon-cell, MBON, and PAM/PPL1 type patterns. It scans the compressed edge list and preserves edges above the 3-synapse starting threshold whenever either endpoint matches a seed neuron. The resulting subgraph includes one-hop partners and is much smaller than the full dataset.

```bash
python -m research.prepare_flywire \
  --connections research/data/raw/fafb-v783/connections_princeton.csv.gz \
  --cell-types research/data/raw/fafb-v783/consolidated_cell_types.csv.gz \
  --output research/data/processed/fafb-v783-mushroom-body
```

The annotation schema is consolidated from multiple sources. Inspect its cell-type labels and change the patterns when needed, for example:

```bash
python -m research.prepare_flywire \
  --connections research/data/raw/fafb-v783/connections_princeton.csv.gz \
  --cell-types research/data/raw/fafb-v783/consolidated_cell_types.csv.gz \
  --output research/data/processed/fafb-v783-mushroom-body \
  --pattern Kenyon --pattern MBON --pattern 'PAM[0-9]' --pattern PPL1
```

## Explore the local result

When the prepared data exists, this notebook cell draws a cell-type-to-cell-type synapse-count heatmap and lists the strongest outgoing cell-type pathways. It reads only the reduced one-hop subgraph, not the full connection table.

```{code-cell} python
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

research_dir = next(path for path in (Path.cwd() / "research", Path.cwd().parent) if (path / "data").exists())
prepared = research_dir / "data/processed/fafb-v783-mushroom-body/mushroom_body_edges.csv.gz"
if prepared.exists():
    edges = pd.read_csv(prepared)
    weight_column = next(name for name in ("syn_count", "weight", "synapses", "n_synapses", "connection_count") if name in edges.columns)
    type_edges = edges.groupby(["pre_type", "post_type"], as_index=False)[weight_column].sum()
    top_types = pd.unique(pd.concat([type_edges["pre_type"], type_edges["post_type"]]))[:24]
    matrix = (type_edges.pivot(index="pre_type", columns="post_type", values=weight_column)
              .reindex(index=top_types, columns=top_types).fillna(0))
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(np.log10(matrix.to_numpy() + 1), cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=90, fontsize=7)
    ax.set_yticks(range(len(matrix.index)), matrix.index, fontsize=7)
    ax.set(xlabel="Postsynaptic annotated type", ylabel="Presynaptic annotated type", title="FlyWire FAFB mushroom-body neighborhood · log₁₀(synapses + 1)")
    fig.colorbar(image, ax=ax, label="log₁₀ synapse count + 1")
    fig.tight_layout()
    display(type_edges.sort_values(weight_column, ascending=False).head(20))
else:
    print("No local FlyWire export found. Follow the download and preparation commands above to create this graph on your machine.")
    print("Raw connectome files are excluded from Git and are never needed to build the public book.")
```

## Source and citation

Use the version and authorship information from the local download manifest. The [FlyWire FAFB v783 connectivity release](https://doi.org/10.5281/zenodo.10676866) is CC BY 4.0; the complete per-neuron connection file is about 852 MB and the synapse-location table about 9.5 GB. See Dorkenwald et al., [*A neuronal wiring diagram of an adult brain*](https://doi.org/10.1038/s41586-024-07558-y), and Shiu et al., [*A Drosophila computational brain model reveals insights into sensorimotor processing*](https://doi.org/10.1038/s41586-024-07763-9). The filtered neighborhood is an analysis derivative; it is not a substitute for the source release, and the static fly-memory model does not yet simulate these real edges.
