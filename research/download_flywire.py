#!/usr/bin/env python3
"""Download FlyWire Codex bulk CSV exports into an ignored local data folder."""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from research.src.flywire_ingest import download_products


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("fafb", "banc"), default="fafb")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    token = os.environ.get("FLYWIRE_CODEX_TOKEN") or getpass.getpass("FlyWire Codex API token (input hidden): ")
    manifest = download_products(arguments.dataset, arguments.output, token)
    for product, details in manifest["files"].items():
        print(f"Downloaded {product}: {details['bytes']:,} bytes; sha256 {details['sha256']}")
    print(f"Manifest saved to {arguments.output / 'download_manifest.json'}")


if __name__ == "__main__":
    main()
