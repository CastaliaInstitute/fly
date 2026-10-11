import csv
import io
import gzip
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import pandas as pd

from research.analyze_flywire_v783 import analyze_release
from research.src.flywire_ingest import download_products, prepare_subgraph


class FlyWireIngestionTests(unittest.TestCase):
    def test_analyze_release_produces_real_data_product_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            annotations = root / "annotations.tsv"
            pd.DataFrame(
                [
                    {"root_id": "101", "cell_class": "Kenyon_Cell", "cell_type": "KCab", "hemibrain_type": "KCab-s", "side": "left", "top_nt": "acetylcholine"},
                    {"root_id": "201", "cell_class": "MBON", "cell_type": "MBON01", "hemibrain_type": "MBON01", "side": "left", "top_nt": "acetylcholine"},
                    {"root_id": "301", "cell_class": "DAN", "cell_type": "PAM01", "hemibrain_type": "PAM01", "side": "left", "top_nt": "dopamine"},
                    {"root_id": "401", "cell_class": "central", "cell_type": "LN01", "hemibrain_type": "LN01", "side": "left", "top_nt": "GABA"},
                ]
            ).to_csv(annotations, sep="\t", index=False)
            connections = root / "connections.feather"
            pd.DataFrame(
                [
                    {"pre_pt_root_id": 101, "post_pt_root_id": 201, "neuropil": "MB_CA_R", "syn_count": 6},
                    {"pre_pt_root_id": 301, "post_pt_root_id": 201, "neuropil": "MB_PED_R", "syn_count": 10},
                    {"pre_pt_root_id": 401, "post_pt_root_id": 101, "neuropil": "AL_R", "syn_count": 8},
                    {"pre_pt_root_id": 201, "post_pt_root_id": 401, "neuropil": "MB_R", "syn_count": 7},
                    {"pre_pt_root_id": 101, "post_pt_root_id": 301, "neuropil": "MB_R", "syn_count": 3},
                ]
            ).to_feather(connections)
            manifest = analyze_release(connections, annotations, root / "processed", root / "site")
            self.assertEqual(manifest["selected_annotated_neurons"]["Kenyon cells"], 1)
            self.assertEqual(manifest["selected_annotated_neurons"]["MBONs"], 1)
            self.assertEqual(manifest["one_hop_connection_rows"], 4)
            self.assertTrue((root / "site/role_connectivity.png").exists())
            roles = pd.read_csv(root / "site/role_connectivity.csv")
            kc_to_mbon = roles[(roles["pre_role"] == "Kenyon cells") & (roles["post_role"] == "MBONs")]
            self.assertEqual(int(kc_to_mbon["synapses"].iloc[0]), 6)

    def test_download_writes_hash_manifest_and_gzip_exports(self):
        payload = gzip.compress(b"root_id,cell_type\n1,Kenyon cell\n")

        class Response(io.BytesIO):
            headers = {"Content-Type": "application/gzip"}
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_):
                self.close()

        with tempfile.TemporaryDirectory() as directory, patch(
            "research.src.flywire_ingest.urllib.request.urlopen",
            side_effect=lambda *_args, **_kwargs: Response(payload),
        ) as open_url:
            manifest = download_products("fafb", Path(directory), "test-token")
            self.assertEqual(open_url.call_count, 2)
            self.assertEqual(manifest["snapshot"], "FAFB v783")
            self.assertTrue((Path(directory) / "connections_princeton.csv.gz").exists())
            self.assertTrue((Path(directory) / "consolidated_cell_types.csv.gz").exists())
            saved = json.loads((Path(directory) / "download_manifest.json").read_text())
            self.assertEqual(saved["files"]["connections_princeton"]["sha256"], manifest["files"]["connections_princeton"]["sha256"])

    def test_extracts_annotated_seeds_and_one_hop_connections(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cell_types = root / "types.csv.gz"
            connections = root / "connections.csv.gz"
            with gzip.open(cell_types, "wt", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=("root_id", "cell_type"))
                writer.writeheader()
                writer.writerows(({"root_id": "kc-1", "cell_type": "Kenyon cell"}, {"root_id": "mbon-1", "cell_type": "MBON-a"}, {"root_id": "other-1", "cell_type": "visual neuron"}))
            with gzip.open(connections, "wt", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=("pre_root_id", "post_root_id", "syn_count"))
                writer.writeheader()
                writer.writerows(({"pre_root_id": "upstream-1", "post_root_id": "kc-1", "syn_count": 4}, {"pre_root_id": "kc-1", "post_root_id": "mbon-1", "syn_count": 6}, {"pre_root_id": "other-1", "post_root_id": "other-2", "syn_count": 9}, {"pre_root_id": "mbon-1", "post_root_id": "kc-1", "syn_count": 1}))
            output = root / "prepared"
            manifest = prepare_subgraph(connections, cell_types, output, patterns=("Kenyon", "MBON"), min_synapses=3)
            self.assertEqual(manifest["dataset"], "FlyWire FAFB v783 snapshot")
            self.assertEqual(manifest["selected_annotated_neurons"], 2)
            self.assertEqual(manifest["one_hop_neurons"], 3)
            self.assertEqual(manifest["retained_connection_rows"], 2)
            with gzip.open(output / "mushroom_body_edges.csv.gz", "rt", encoding="utf-8", newline="") as file:
                self.assertEqual(len(list(csv.DictReader(file))), 2)


if __name__ == "__main__":
    unittest.main()
