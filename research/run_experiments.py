#!/usr/bin/env python3
"""Run seeded memory experiments, summarize responses, and save publication-ready plots."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from research.src.fly_memory import (
    acquisition_experiment,
    extinction_experiment,
    mean_sem,
    reversal_experiment,
    summarize_experiments,
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot(acquisition: list[dict], extinction: list[dict], reversal: list[dict], out: Path) -> None:
    acquisition_summary = mean_sem(acquisition, group_by=("group", "trial"))
    extinction_summary = mean_sem(extinction, group_by=("phase", "trial"))
    reversal_summary = mean_sem(reversal, group_by=("phase", "trial"))

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for group, color in (("paired", "#52694f"), ("cue-only control", "#bd704b")):
        rows = [row for row in acquisition_summary if row["group"] == group]
        x = np.array([row["trial"] for row in rows])
        y = np.array([row["mean"] for row in rows])
        sem = np.array([row["sem"] for row in rows])
        ax.plot(x, y, marker="o", ms=3, color=color, label=group)
        ax.fill_between(x, y - sem, y + sem, color=color, alpha=0.16, linewidth=0)
    ax.axhline(0, color="#99998f", linewidth=0.8)
    ax.set(xlabel="Cue–outcome pairings", ylabel="Predicted cue value", title="Acquisition")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "acquisition.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, summary, phases, title in (
        (axes[0], extinction_summary, ("after acquisition", "cue only"), "Extinction"),
        (axes[1], reversal_summary, ("sugar", "bitter reversal"), "Reversal"),
    ):
        for phase, color in zip(phases, ("#52694f", "#bd704b")):
            rows = [row for row in summary if row["phase"] == phase]
            x = np.array([row["trial"] for row in rows])
            y = np.array([row["mean"] for row in rows])
            sem = np.array([row["sem"] for row in rows])
            ax.plot(x, y, marker="o", ms=3, color=color, label=phase)
            ax.fill_between(x, y - sem, y + sem, color=color, alpha=0.16, linewidth=0)
        ax.axhline(0, color="#99998f", linewidth=0.8)
        ax.set(xlabel="Trials within phase", ylabel="Predicted cue value", title=title)
        ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out / "extinction-reversal.png", dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicates", type=int, default=40)
    parser.add_argument("--output", type=Path, default=Path("research/results"))
    args = parser.parse_args()
    if args.replicates < 2:
        parser.error("--replicates must be at least 2 to estimate standard errors")
    args.output.mkdir(parents=True, exist_ok=True)

    acquisition = acquisition_experiment(replicates=args.replicates, trials=12, seed=2026)
    extinction = extinction_experiment(replicates=args.replicates, acquisition_trials=10, extinction_trials=16, seed=3026)
    reversal = reversal_experiment(replicates=args.replicates, acquisition_trials=10, reversal_trials=16, seed=4026)
    summary = summarize_experiments(acquisition, extinction, reversal)
    for name, rows in (("acquisition", acquisition), ("extinction", extinction), ("reversal", reversal)):
        _write_csv(args.output / f"{name}.csv", rows)
    _write_csv(args.output / "summary.csv", summary)
    _plot(acquisition, extinction, reversal, args.output)
    manifest = {
        "model": "synthetic mushroom-body-inspired toy circuit; see research/book/methods.md",
        "replicates": args.replicates,
        "experiment_seeds": {"acquisition": 2026, "extinction": 3026, "reversal": 4026},
        "acquisition_trials": 12,
        "extinction": {"acquisition_trials": 10, "unreinforced_trials": 16},
        "reversal": {"acquisition_trials": 10, "bitter_trials": 16},
        "data_source": "No real FlyWire edges used in these simulations.",
    }
    (args.output / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for row in summary:
        print(f"{row['metric']}: {row['mean']:.4f} ± {row['sem']:.4f} ({row['n']} model initializations; {row['unit']})")
    print(f"Saved replicate CSVs, summary, manifest, and graphs under {args.output}")


if __name__ == "__main__":
    main()
