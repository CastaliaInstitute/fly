---
title: Associative-memory experiments
kernelspec:
  name: python3
  display_name: Python 3
---

This chapter runs the conditioning, extinction, and reversal protocols across seeded replicates and plots the simulated cue-value response. Run each experiment separately or change the seeds, trial counts, and model parameters to explore the assumptions.

## Load the model and plotting tools

```{code-cell} python
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

research_dir = next(path for path in (Path.cwd() / "research", Path.cwd().parent) if (path / "src" / "fly_memory.py").exists())
sys.path.insert(0, str(research_dir / "src"))
from fly_memory import (
    ModelParameters,
    MushroomBodyToy,
    acquisition_experiment,
    extinction_experiment,
    mean_sem,
    reversal_experiment,
)

plt.rcParams.update({"figure.figsize": (8, 4.5), "axes.spines.top": False, "axes.spines.right": False})
```

## Sanity check one circuit

Before running replicates, inspect one model: an untrained cue has neutral value; sugar pairing makes its predicted value positive; bitter pairing makes it negative.

```{code-cell} python
circuit = MushroomBodyToy(ModelParameters(seed=17))
baseline = circuit.recall("A")["value"]
for _ in range(5):
    circuit.condition("A", outcome=1)
after_sugar = circuit.recall("A")["value"]
for _ in range(8):
    circuit.condition("A", outcome=-1)
after_reversal = circuit.recall("A")["value"]

print(f"Before training: {baseline:+.3f}")
print(f"After sugar pairing: {after_sugar:+.3f}")
print(f"After bitter reversal: {after_reversal:+.3f}")
assert baseline == 0 and after_sugar > 0 and after_reversal < after_sugar
```

## Acquisition and cue-only control

The cue-only control receives presentations without a cue-contingent teaching signal. Each line is a mean over independent initializations; the shading is ±1 standard error across simulated replicates.

```{code-cell} python
acquisition = acquisition_experiment(replicates=40, trials=12, seed=2026)
acquisition_summary = mean_sem(acquisition, group_by=("group", "trial"))

fig, ax = plt.subplots()
for group, color in (("paired", "#52694f"), ("cue-only control", "#bd704b")):
    rows = [row for row in acquisition_summary if row["group"] == group]
    x = np.array([row["trial"] for row in rows])
    mean = np.array([row["mean"] for row in rows])
    sem = np.array([row["sem"] for row in rows])
    ax.plot(x, mean, marker="o", ms=3, color=color, label=group)
    ax.fill_between(x, mean - sem, mean + sem, color=color, alpha=0.16, linewidth=0)
ax.axhline(0, color="#99998f", linewidth=0.8)
ax.set(xlabel="Cue–outcome pairings", ylabel="Predicted cue value", title="Acquisition in the toy circuit")
ax.legend(frameon=False)
fig.tight_layout()
```

## Extinction and reversal

The plot separates the two post-acquisition manipulations. Extinction is modeled as weight decay during cue-only trials; reversal learns an opponent-valence association. Those are deliberately different assumptions.

```{code-cell} python
extinction = extinction_experiment(replicates=40, acquisition_trials=10, extinction_trials=16, seed=3026)
reversal = reversal_experiment(replicates=40, acquisition_trials=10, reversal_trials=16, seed=4026)
ext_summary = mean_sem(extinction, group_by=("phase", "trial"))
rev_summary = mean_sem(reversal, group_by=("phase", "trial"))

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, summary, phases, title in (
    (axes[0], ext_summary, ("after acquisition", "cue only"), "Extinction"),
    (axes[1], rev_summary, ("sugar", "bitter reversal"), "Reversal learning"),
):
    for phase, color in zip(phases, ("#52694f", "#bd704b")):
        rows = [row for row in summary if row["phase"] == phase]
        x = np.array([row["trial"] for row in rows])
        mean = np.array([row["mean"] for row in rows])
        sem = np.array([row["sem"] for row in rows])
        ax.plot(x, mean, marker="o", ms=3, color=color, label=phase)
        ax.fill_between(x, mean - sem, mean + sem, color=color, alpha=0.16, linewidth=0)
    ax.axhline(0, color="#99998f", linewidth=0.8)
    ax.set(xlabel="Trials within phase", ylabel="Predicted cue value", title=title)
    ax.legend(frameon=False)
fig.tight_layout()
```

## Export reproducible results

Save the unaggregated replicate-level results as CSV. The records include experiment phase, replicate seed index, trial number, and response; the cell below writes only generated results, never a real connectome export.

```{code-cell} python
import csv

result_dir = research_dir / "results"
result_dir.mkdir(parents=True, exist_ok=True)
for name, rows in (("acquisition", acquisition), ("extinction", extinction), ("reversal", reversal)):
    output = result_dir / f"{name}.csv"
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows):,} replicate-trial rows to {output}")
```
