import csv
import io
import gzip
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from research.src.flywire_ingest import download_products, prepare_subgraph


class FlyWireIngestionTests(unittest.TestCase):
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
