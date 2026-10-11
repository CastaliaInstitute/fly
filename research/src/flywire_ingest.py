"""Local FlyWire Codex downloads and one-hop mushroom-body subgraph export."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


CODEX_PRODUCTS = {
    "connections_princeton": "connections_princeton.csv.gz",
    "consolidated_cell_types": "consolidated_cell_types.csv.gz",
}
DEFAULT_PATTERNS = (r"kenyon", r"mbon", r"\bpam\b", r"\bppl1\b")
SNAPSHOTS = {"fafb": "v783", "banc": "v888"}


def download_products(dataset: str, output: Path, token: str) -> dict:
    """Download official Codex compressed CSV exports without exposing the token."""
    if not token:
        raise ValueError("A Codex API token is required.")
    if dataset not in {"fafb", "banc"}:
        raise ValueError("Codex bulk downloads currently support 'fafb' and 'banc'.")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": "FlyWire Codex static download export",
        "dataset": dataset,
        "snapshot": f"{dataset.upper()} {SNAPSHOTS[dataset]}",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "files": {},
    }

    for product, filename in CODEX_PRODUCTS.items():
        query = urllib.parse.urlencode({"data_product": product, "dataset": dataset, "api_token": token})
        url = f"https://codex.flywire.ai/api/download_resource?{query}"
        destination = output / filename
        digest = hashlib.sha256()
        with tempfile.NamedTemporaryFile(dir=output, suffix=".part", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "Castalia-Fly-Memory-Research/1.0"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    content_type = response.headers.get("Content-Type", "")
                    if "json" in content_type.lower():
                        body = response.read(2048).decode("utf-8", errors="replace")
                        raise RuntimeError(f"Codex did not return the {product} file (HTTP {response.status}): {body[:300]}")
                    while chunk := response.read(1024 * 1024):
                        temporary.write(chunk)
                        digest.update(chunk)
            except urllib.error.HTTPError as error:
                explanation = "Sign in to Codex and check your API token." if error.code in (401, 403) else f"Codex HTTP {error.code}."
                raise RuntimeError(f"Could not download {product}. {explanation}") from error
            except Exception:
                temporary_path.unlink(missing_ok=True)
                raise
        temporary_path.replace(destination)
        try:
            with gzip.open(destination, "rt", encoding="utf-8", newline="") as compressed:
                if not compressed.readline():
                    raise ValueError("empty gzip CSV")
        except Exception as error:
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"Codex response for {product} was not a readable gzip CSV.") from error
        manifest["files"][product] = {"filename": filename, "sha256": digest.hexdigest(), "bytes": destination.stat().st_size}

    (output / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _column(headers: list[str], candidates: Iterable[str], *, context: str) -> str:
    indexed = {header.strip().lower(): header for header in headers}
    for candidate in candidates:
        if candidate in indexed:
            return indexed[candidate]
    raise ValueError(f"Could not identify {context} in CSV columns: {', '.join(headers)}")


def prepare_subgraph(
    connections_path: Path,
    cell_types_path: Path,
    output: Path,
    *,
    dataset: str = "fafb",
    patterns: Iterable[str] = DEFAULT_PATTERNS,
    min_synapses: int = 3,
) -> dict:
    """Extract connections incident to annotated mushroom-body neuron types.

    Both connection endpoints are retained, so output includes a one-hop context
    around selected Kenyon cells, MBONs, and PAM/PPL1 dopamine neurons.
    """
    if min_synapses < 1:
        raise ValueError("min_synapses must be >= 1.")
    if dataset not in SNAPSHOTS:
        raise ValueError(f"Unknown dataset {dataset!r}; expected one of {', '.join(SNAPSHOTS)}.")
    patterns = tuple(patterns)
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    if not regexes:
        raise ValueError("At least one cell-type pattern is required.")

    with gzip.open(cell_types_path, "rt", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        headers = reader.fieldnames or []
        root_col = _column(headers, ("root_id", "rootid", "pt_root_id", "id"), context="cell root ID")
        selected: dict[str, dict[str, str]] = {}
        label_cols = [h for h in headers if h.strip().lower() not in {root_col.lower(), "root_id", "rootid"}]
        for row in reader:
            root_id = (row.get(root_col) or "").strip()
            if not root_id:
                continue
            labels = [str(row.get(col) or "").strip() for col in label_cols]
            readable = " | ".join(label for label in labels if label)
            if any(regex.search(readable) for regex in regexes):
                selected[root_id] = {"root_id": root_id, "cell_type": readable}
    if not selected:
        raise ValueError("No annotated cells matched the patterns. Inspect the annotation export or supply --pattern values.")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    edge_path = output / "mushroom_body_edges.csv.gz"
    node_ids = set(selected)
    edge_count = 0
    with gzip.open(connections_path, "rt", encoding="utf-8-sig", newline="") as source, gzip.open(edge_path, "wt", encoding="utf-8", newline="") as compressed:
        reader = csv.DictReader(source)
        headers = reader.fieldnames or []
        pre_col = _column(headers, ("pre_root_id", "pre_pt_root_id", "pre_id", "source"), context="presynaptic ID")
        post_col = _column(headers, ("post_root_id", "post_pt_root_id", "post_id", "target"), context="postsynaptic ID")
        weight_col = _column(headers, ("syn_count", "weight", "synapses", "n_synapses", "connection_count"), context="synapse count")
        output_headers = [*headers, "pre_type", "post_type", "is_mushroom_body_seed"]
        writer = csv.DictWriter(compressed, fieldnames=output_headers)
        writer.writeheader()
        for row in reader:
            pre = (row.get(pre_col) or "").strip()
            post = (row.get(post_col) or "").strip()
            try:
                weight = float(row.get(weight_col) or 0)
            except ValueError:
                continue
            if weight < min_synapses or (pre not in selected and post not in selected):
                continue
            node_ids.update((pre, post))
            writer.writerow({**row, "pre_type": selected.get(pre, {}).get("cell_type", "other partner"), "post_type": selected.get(post, {}).get("cell_type", "other partner"), "is_mushroom_body_seed": str(pre in selected or post in selected).lower()})
            edge_count += 1

    with (output / "mushroom_body_nodes.csv").open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=("root_id", "cell_type", "is_mushroom_body_seed"))
        writer.writeheader()
        for root_id in sorted(node_ids):
            writer.writerow({"root_id": root_id, "cell_type": selected.get(root_id, {}).get("cell_type", "other partner"), "is_mushroom_body_seed": str(root_id in selected).lower()})

    manifest = {
        "dataset": f"FlyWire {dataset.upper()} {SNAPSHOTS[dataset]} snapshot",
        "connections_source": Path(connections_path).name,
        "cell_types_source": Path(cell_types_path).name,
        "cell_type_patterns": list(patterns),
        "min_synapses": min_synapses,
        "selected_annotated_neurons": len(selected),
        "one_hop_neurons": len(node_ids),
        "retained_connection_rows": edge_count,
        "license": "CC BY 4.0; cite the source data and papers",
    }
    (output / "subgraph_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
