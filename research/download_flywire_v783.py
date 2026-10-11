#!/usr/bin/env python3
"""Download the open FlyWire FAFB v783 edge table and pinned annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


CONNECTIONS_URL = "https://zenodo.org/api/records/10676866/files/proofread_connections_783.feather/content"
ANNOTATIONS_COMMIT = "a83b2776d60d5764cef36b927f5f9679c16c47a2"
ANNOTATIONS_URL = (
    "https://raw.githubusercontent.com/flyconnectome/flywire_annotations/"
    f"{ANNOTATIONS_COMMIT}/supplemental_files/Supplemental_file1_neuron_annotations.tsv"
)
EXPECTED_MD5 = "f48f972d262323a102aed49af1396b8a"
FILES = {
    "Supplemental_file1_neuron_annotations.tsv": (ANNOTATIONS_URL, None),
    "proofread_connections_783.feather": (CONNECTIONS_URL, EXPECTED_MD5),
}
RANGE_CHUNK_SIZE = 64 * 1024 * 1024
MAX_PARALLEL_RANGES = 8


def _download(url: str, destination: Path, expected_md5: str | None = None) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".part", delete=False) as output:
        temporary = Path(output.name)
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()
        transferred = 0
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Castalia-Fly-Memory-Research/1.0"})
            with urllib.request.urlopen(request, timeout=120) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    sha256.update(chunk)
                    md5.update(chunk)
                    transferred += len(chunk)
                    if destination.name.endswith(".feather") and transferred % (100 * 1024 * 1024) < len(chunk):
                        print(f"  Downloaded {transferred / (1024 * 1024):,.0f} MiB")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    actual_md5 = md5.hexdigest()
    if expected_md5 and actual_md5 != expected_md5:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Checksum mismatch for {destination.name}: expected {expected_md5}, got {actual_md5}.")
    temporary.replace(destination)
    return {"url": url, "bytes": transferred, "sha256": sha256.hexdigest(), "md5": actual_md5}


def _download_range(url: str, start: int, end: int, part: Path, total: int) -> int:
    expected_size = end - start + 1
    offset = part.stat().st_size if part.exists() else 0
    if offset == expected_size:
        return expected_size
    if offset > expected_size:
        part.unlink()
        offset = 0
    transferred = offset
    attempts = 0
    while transferred < expected_size:
        request = urllib.request.Request(url, headers={"Range": f"bytes={start + transferred}-{end}", "User-Agent": "Castalia-Fly-Memory-Research/1.0"})
        before = transferred
        mode = "ab" if transferred else "wb"
        with urllib.request.urlopen(request, timeout=120) as response, part.open(mode) as output:
            if response.status != 206:
                raise RuntimeError(f"Zenodo did not honor byte-range request {start + transferred}-{end} (HTTP {response.status}).")
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
                transferred += len(chunk)
        if transferred == before:
            attempts += 1
            if attempts >= 5:
                raise RuntimeError(f"No progress downloading FlyWire range {start}-{end}; partial data is retained for retry.")
            time.sleep(attempts)
    if transferred != expected_size:
        raise RuntimeError(f"Incomplete FlyWire range {start}-{end}: got {transferred} of {expected_size} bytes.")
    return expected_size


def _download_connection_table(url: str, destination: Path) -> dict:
    """Fetch the large Feather file in resumable parallel HTTP range chunks."""
    total = 852_022_274  # Published file size in Zenodo record 10676866.
    parts_dir = destination.parent / ".proofread_connections_783.parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    ranges = []
    for start in range(0, total, RANGE_CHUNK_SIZE):
        end = min(start + RANGE_CHUNK_SIZE, total) - 1
        part = parts_dir / f"part-{start // RANGE_CHUNK_SIZE:04d}"
        ranges.append((start, end, part))
    lock = threading.Lock()
    completed = 0
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_RANGES) as pool:
        futures = {pool.submit(_download_range, url, start, end, part, total): (start, end) for start, end, part in ranges}
        for future in as_completed(futures):
            size = future.result()
            with lock:
                completed += size
                print(f"  Retrieved {completed / (1024 * 1024):,.0f} / {total / (1024 * 1024):,.0f} MiB", flush=True)

    temporary = destination.with_suffix(destination.suffix + ".part")
    with temporary.open("wb") as combined:
        for _, _, part in ranges:
            with part.open("rb") as source:
                shutil.copyfileobj(source, combined, length=4 * 1024 * 1024)
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with temporary.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            md5.update(chunk)
            sha256.update(chunk)
    actual_md5 = md5.hexdigest()
    if actual_md5 != EXPECTED_MD5:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Checksum mismatch for {destination.name}: expected {EXPECTED_MD5}, got {actual_md5}.")
    temporary.replace(destination)
    shutil.rmtree(parts_dir)
    for stale in destination.parent.glob("*.part"):
        stale.unlink(missing_ok=True)
    return {"url": url, "bytes": total, "sha256": sha256.hexdigest(), "md5": actual_md5}


def download_release(output: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    required = 950 * 1024 * 1024
    if shutil.disk_usage(output).free < required:
        raise OSError("At least 950 MiB free disk space is required for the v783 edge table and annotation file.")

    manifest = {
        "dataset": "FlyWire female adult brain (FAFB), public snapshot v783",
        "connectivity_record": "https://doi.org/10.5281/zenodo.10676866",
        "annotation_repository_commit": ANNOTATIONS_COMMIT,
        "license": "CC BY 4.0 for the Zenodo connectivity release; retain source attribution for annotations",
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
        "files": {},
    }
    for filename, (url, checksum) in FILES.items():
        destination = output / filename
        if destination.exists():
            actual_md5 = hashlib.md5(destination.read_bytes()).hexdigest()
            if checksum and actual_md5 != checksum:
                destination.unlink()
            else:
                digest = hashlib.sha256(destination.read_bytes()).hexdigest()
                manifest["files"][filename] = {"url": url, "bytes": destination.stat().st_size, "sha256": digest, "md5": actual_md5}
                print(f"Using existing {filename} ({destination.stat().st_size:,} bytes).", flush=True)
                continue
        print(f"Downloading {filename} …")
        if filename == "proofread_connections_783.feather":
            manifest["files"][filename] = _download_connection_table(url, destination)
        else:
            manifest["files"][filename] = _download(url, destination, checksum)
        print(f"  {manifest['files'][filename]['bytes']:,} bytes; SHA-256 {manifest['files'][filename]['sha256']}")
    (output / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("research/data/raw/fafb-v783-public"))
    args = parser.parse_args()
    download_release(args.output)


if __name__ == "__main__":
    main()
