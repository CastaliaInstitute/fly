#!/usr/bin/env python3
"""Create a local, annotated one-hop graph around mushroom-body neuron types."""

from __future__ import annotations

import argparse
from pathlib import Path

from research.src.flywire_ingest import DEFAULT_PATTERNS, prepare_subgraph


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connections", type=Path, required=True, help="Codex connections_princeton.csv.gz")
    parser.add_argument("--cell-types", type=Path, required=True, help="Codex consolidated_cell_types.csv.gz")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", choices=("fafb", "banc"), default="fafb")
    parser.add_argument("--min-synapses", type=int, default=3)
    parser.add_argument("--pattern", action="append", dest="patterns", help="Case-insensitive regex matching cell annotations; repeat as needed.")
    args = parser.parse_args()
    manifest = prepare_subgraph(args.connections, args.cell_types, args.output, dataset=args.dataset, patterns=args.patterns or DEFAULT_PATTERNS, min_synapses=args.min_synapses)
    print(f"Selected {manifest['selected_annotated_neurons']:,} annotated seed neurons.")
    print(f"Wrote {manifest['retained_connection_rows']:,} one-hop connection rows for {manifest['one_hop_neurons']:,} neurons to {args.output}.")


if __name__ == "__main__":
    main()
