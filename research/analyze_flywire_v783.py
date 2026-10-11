#!/usr/bin/env python3
"""Analyze real FlyWire v783 directed connections around annotated MB cell classes."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow
import pyarrow.feather as feather


ROLE_ORDER = ("Kenyon cells", "MBONs", "PAM/PPL1 DANs", "other partners")


def load_mushroom_body_annotations(path: Path) -> pd.DataFrame:
    annotations = pd.read_csv(
        path,
        sep="\t",
        usecols=("root_id", "cell_class", "cell_type", "hemibrain_type", "side", "top_nt"),
        dtype={"root_id": "string", "cell_class": "string", "cell_type": "string"},
        keep_default_na=False,
    )
    annotations["role"] = ""
    annotations.loc[annotations["cell_class"].eq("Kenyon_Cell"), "role"] = "Kenyon cells"
    annotations.loc[annotations["cell_class"].eq("MBON"), "role"] = "MBONs"
    dan_pattern = annotations["cell_class"].eq("DAN") & annotations["cell_type"].str.match(r"^(PAM|PPL1)", case=False)
    annotations.loc[dan_pattern, "role"] = "PAM/PPL1 DANs"
    return annotations.loc[annotations["role"].ne("")].copy()


def analyze_release(connections_path: Path, annotations_path: Path, output: Path, site_output: Path) -> dict:
    """Summarize directed weighted edges touching MB cells and immediate partners."""
    annotations = load_mushroom_body_annotations(annotations_path)
    ids = set(annotations["root_id"].astype(str))
    role_by_id = annotations.set_index("root_id")["role"].to_dict()
    label_by_id = annotations.set_index("root_id")["cell_type"].to_dict()

    edge_table = feather.read_table(
        connections_path,
        columns=("pre_pt_root_id", "post_pt_root_id", "neuropil", "syn_count"),
        memory_map=True,
    )
    edges = edge_table.to_pandas()
    edges["pre_pt_root_id"] = edges["pre_pt_root_id"].astype("string")
    edges["post_pt_root_id"] = edges["post_pt_root_id"].astype("string")
    edges["syn_count"] = pd.to_numeric(edges["syn_count"], errors="coerce").fillna(0)

    # FAFB Codex's default connection threshold is 5 synapses per neuron pair.
    pair_weights = edges.groupby(["pre_pt_root_id", "post_pt_root_id"], observed=True)["syn_count"].sum()
    qualifying = pair_weights[pair_weights >= 5].rename("pair_syn_count").reset_index()
    edges = edges.merge(qualifying, on=["pre_pt_root_id", "post_pt_root_id"], how="inner")
    edges["pre_role"] = edges["pre_pt_root_id"].map(role_by_id).fillna("other partners")
    edges["post_role"] = edges["post_pt_root_id"].map(role_by_id).fillna("other partners")
    edges["pre_cell_type"] = edges["pre_pt_root_id"].map(label_by_id).fillna("other partner").replace("", "other partner")
    edges["post_cell_type"] = edges["post_pt_root_id"].map(label_by_id).fillna("other partner").replace("", "other partner")
    neighborhood = edges[edges["pre_pt_root_id"].isin(ids) | edges["post_pt_root_id"].isin(ids)].copy()
    neighborhood["neuron_pair"] = neighborhood["pre_pt_root_id"] + "→" + neighborhood["post_pt_root_id"]

    output = Path(output)
    site_output = Path(site_output)
    output.mkdir(parents=True, exist_ok=True)
    site_output.mkdir(parents=True, exist_ok=True)
    neighborhood.to_csv(output / "mushroom_body_neighborhood.csv.gz", index=False, compression="gzip")

    role_summary = (
        neighborhood.groupby(["pre_role", "post_role"], observed=True)
        .agg(synapses=("syn_count", "sum"), neuropil_rows=("syn_count", "size"), neuron_pairs=("neuron_pair", "nunique"))
        .reset_index()
    )
    role_summary.to_csv(output / "role_connectivity.csv", index=False)
    role_summary.to_csv(site_output / "role_connectivity.csv", index=False)

    neuropil_summary = (
        neighborhood.groupby(["neuropil", "pre_role", "post_role"], observed=True)["syn_count"]
        .sum()
        .reset_index(name="synapses")
    )
    neuropil_summary.to_csv(output / "role_neuropil_connectivity.csv", index=False)
    neuropil_summary.to_csv(site_output / "role_neuropil_connectivity.csv", index=False)

    type_pairs = (
        neighborhood.groupby(["pre_role", "pre_cell_type", "post_role", "post_cell_type"], observed=True)
        .agg(synapses=("syn_count", "sum"), neuron_pairs=("neuron_pair", "nunique"))
        .reset_index()
        .sort_values("synapses", ascending=False)
        .head(30)
    )
    type_pairs.to_csv(output / "strongest_cell_type_pairs.csv", index=False)
    type_pairs.to_csv(site_output / "strongest_cell_type_pairs.csv", index=False)

    role_summary["pre_role"] = pd.Categorical(role_summary["pre_role"], ROLE_ORDER, ordered=True)
    role_summary["post_role"] = pd.Categorical(role_summary["post_role"], ROLE_ORDER, ordered=True)
    role_matrix = role_summary.pivot(index="pre_role", columns="post_role", values="synapses").reindex(index=ROLE_ORDER, columns=ROLE_ORDER).fillna(0)
    fig, ax = plt.subplots(figsize=(7.2, 5.5))
    image = ax.imshow(np.log10(role_matrix.to_numpy(dtype=float) + 1), cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(ROLE_ORDER)), ROLE_ORDER, rotation=35, ha="right")
    ax.set_yticks(range(len(ROLE_ORDER)), ROLE_ORDER)
    ax.set(xlabel="Postsynaptic annotation group", ylabel="Presynaptic annotation group", title="FAFB v783: one-hop mushroom-body neighborhood")
    for y in range(len(ROLE_ORDER)):
        for x in range(len(ROLE_ORDER)):
            ax.text(x, y, f"{role_matrix.iloc[y, x]:,.0f}", ha="center", va="center", fontsize=8, color="#182b32")
    fig.colorbar(image, ax=ax, label="log₁₀(synapses + 1)")
    fig.tight_layout()
    fig.savefig(output / "role_connectivity.png", dpi=190)
    fig.savefig(site_output / "role_connectivity.png", dpi=190)
    plt.close(fig)

    top_neuropils = neuropil_summary.groupby("neuropil", observed=True)["synapses"].sum().nlargest(14).sort_values()
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(top_neuropils.index.astype(str), top_neuropils.values, color="#52694f")
    ax.set(xlabel="Synapses on retained directed edges", title="Leading neuropils in the selected one-hop neighborhood")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output / "leading_neuropils.png", dpi=190)
    fig.savefig(site_output / "leading_neuropils.png", dpi=190)
    plt.close(fig)

    role_counts = {str(role): int(count) for role, count in annotations["role"].value_counts().items()}
    source_manifest_path = Path(connections_path).parent / "download_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8")) if source_manifest_path.exists() else None
    manifest = {
        "dataset": "FlyWire FAFB v783",
        "source_connectivity": "proofread_connections_783.feather",
        "source_annotations": "Supplemental_file1_neuron_annotations.tsv",
        "synapse_threshold": 5,
        "threshold_semantics": "Directed neuron-pair total across neuropils, using FAFB's 5-synapse starting threshold.",
        "selected_annotated_neurons": role_counts,
        "qualifying_neuron_pairs_in_full_table": int(len(qualifying)),
        "one_hop_connection_rows": int(len(neighborhood)),
        "one_hop_unique_neuron_pairs": int(neighborhood[["pre_pt_root_id", "post_pt_root_id"]].drop_duplicates().shape[0]),
        "raw_synapse_count_used_as_weight": "syn_count is an anatomical count, not a measured synaptic efficacy or signed neural weight.",
        "citation": "Dorkenwald et al. 2024, doi:10.1038/s41586-024-07558-y; FlyWire annotations release v783.",
        "license": "Connectivity release CC BY 4.0.",
        "annotation_repository_commit": source_manifest.get("annotation_repository_commit") if source_manifest else None,
        "input_hashes": source_manifest["files"] if source_manifest else "Unavailable; download with download_flywire_v783.py to record input hashes.",
        "software": {"pandas": pd.__version__, "pyarrow": pyarrow.__version__},
        "analyzed_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (site_output / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connections", type=Path, default=Path("research/data/raw/fafb-v783-public/proofread_connections_783.feather"))
    parser.add_argument("--annotations", type=Path, default=Path("research/data/raw/fafb-v783-public/Supplemental_file1_neuron_annotations.tsv"))
    parser.add_argument("--output", type=Path, default=Path("research/data/processed/fafb-v783-mushroom-body-public"))
    parser.add_argument("--site-output", type=Path, default=Path("research/book/assets/flywire-v783"))
    args = parser.parse_args()
    manifest = analyze_release(args.connections, args.annotations, args.output, args.site_output)
    print(json.dumps(manifest, indent=2))
    print(f"Aggregated plots and tables written to {args.site_output}")


if __name__ == "__main__":
    main()
