# Fly memory research workspace

This workspace contains the executable Jupyter Book, deterministic associative-memory experiments, and tools for exploring the adult female FlyWire brain connectome.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r research/requirements.txt
python -m unittest discover -s research/tests -v
jupyter book build research/book --html --execute
```

The book renders to `research/book/_build/html/`. The experiment notebook and model run without external data. Real FlyWire files are downloaded locally through the Codex export flow below; raw and processed connectome files are excluded from Git.

## Download and prepare FlyWire v783

1. Sign in to [FlyWire Codex](https://codex.flywire.ai/) and create/copy a Codex API token from your account page. The token is private; do not put it in a notebook, a command-line argument, or a committed file.
2. Set it only in your local shell, then fetch the FAFB v783 connection and cell-type exports:

   ```bash
   read -s FLYWIRE_CODEX_TOKEN
   export FLYWIRE_CODEX_TOKEN
   python -m research.download_flywire --dataset fafb --output research/data/raw/fafb-v783
   ```

3. Extract a local mushroom-body neighborhood from annotated Kenyon cells, mushroom-body output neurons, and dopamine teaching neurons:

   ```bash
   python -m research.prepare_flywire \
     --connections research/data/raw/fafb-v783/connections_princeton.csv.gz \
     --cell-types research/data/raw/fafb-v783/consolidated_cell_types.csv.gz \
     --output research/data/processed/fafb-v783-mushroom-body
   ```

The preparation step retains directed connections with at least three synapses when either endpoint is tagged by the configured mushroom-body type patterns. This is a one-hop neighborhood for exploration, not a claim that the resulting subgraph is a complete functional memory circuit. The book's FlyWire chapter reads that prepared local export when it exists; otherwise it explains how to produce it. Users can provide different type patterns for the exports available to them.

## Sources, versioning, and limits

- The download targets Codex's current static **FAFB** export, currently identified as v783. Each local download writes a manifest with the dataset, file hashes, and preparation criteria. Re-check the Codex dataset/version page before comparing results across time.
- The official FlyWire FAFB release is open access under **CC BY 4.0**. See the [Zenodo record](https://doi.org/10.5281/zenodo.10676866) and [FlyWire connectome papers](https://codex.flywire.ai/about_flywire). Cite the primary dataset and papers in any downstream work.
- A connectome supplies structural connectivity, not learned synaptic state or a validated learning rule. The Python memory model remains a transparent toy model; the FlyWire files are explored separately until a scientifically justified mapping between them is implemented.
- The full Zenodo connection table is about 852 MB; the much larger synapse-location table is about 9.5 GB. This project does not download or publish the raw tables by default.
