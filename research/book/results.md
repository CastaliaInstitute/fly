---
title: Results and conclusions
kernelspec:
  name: python3
  display_name: Python 3
---

This report processes replicate-level outputs from the seeded acquisition, extinction, and reversal protocols. Re-run the code cells to regenerate the values from the source model. The results describe the **specified toy model**, not observed flies.

## Run and process the experiments

Each simulated initialization gets its own deterministic Kenyon-cell cue patterns. The response measure is the mean appetitive weight minus mean aversive weight over the active cue cells. The table reports means and standard errors across 40 model initializations; these are not biological sampling errors.

```{code-cell} python
from pathlib import Path
import sys

import pandas as pd

research_dir = next(path for path in (Path.cwd() / "research", Path.cwd().parent) if (path / "src" / "fly_memory.py").exists())
sys.path.insert(0, str(research_dir / "src"))
from fly_memory import acquisition_experiment, extinction_experiment, reversal_experiment, summarize_experiments

acquisition = acquisition_experiment(replicates=40, trials=12, seed=2026)
extinction = extinction_experiment(replicates=40, acquisition_trials=10, extinction_trials=16, seed=3026)
reversal = reversal_experiment(replicates=40, acquisition_trials=10, reversal_trials=16, seed=4026)
summary_rows = summarize_experiments(acquisition, extinction, reversal)
summary = pd.DataFrame(summary_rows)
summary[["metric", "description", "mean", "sem", "n", "unit"]].round(4)
```

## Processed results

The figure below reports the acquisition, extinction, and reversal trajectories, with the exact underlying simulated values summarized in the table above.

```{code-cell} python
import matplotlib.pyplot as plt
import numpy as np
from fly_memory import mean_sem

acq_summary = mean_sem(acquisition, group_by=("group", "trial"))
ext_summary = mean_sem(extinction, group_by=("phase", "trial"))
rev_summary = mean_sem(reversal, group_by=("phase", "trial"))
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, records, group_key, groups, title in (
    (axes[0], acq_summary, "group", ("paired", "cue-only control"), "Acquisition"),
    (axes[1], ext_summary, "phase", ("after acquisition", "cue only"), "Extinction"),
    (axes[2], rev_summary, "phase", ("sugar", "bitter reversal"), "Reversal"),
):
    for group, color in zip(groups, ("#52694f", "#bd704b")):
        rows = [row for row in records if row[group_key] == group]
        x = np.asarray([row["trial"] for row in rows])
        y = np.asarray([row["mean"] for row in rows])
        sem = np.asarray([row["sem"] for row in rows])
        ax.plot(x, y, color=color, marker="o", ms=2.5, label=group)
        ax.fill_between(x, y-sem, y+sem, color=color, alpha=.15, linewidth=0)
    ax.axhline(0, color="#99998f", linewidth=.8)
    ax.set(title=title, xlabel="Trial", ylabel="Predicted cue value")
    ax.legend(frameon=False, fontsize=8)
fig.tight_layout()
```

## Conclusions for this parameterization

```{code-cell} python
metrics = {row["metric"]: row for row in summary_rows}
paired = metrics["paired_at_acquisition_end"]["mean"]
control = metrics["cue_only_control_at_acquisition_end"]["mean"]
start = metrics["extinction_start"]["mean"]
end = metrics["extinction_end"]["mean"]
reversal_start = metrics["reversal_start"]["mean"]
reversal_end = metrics["reversal_end"]["mean"]
negative_share = metrics["reversal_negative_fraction"]["mean"]

print(f"1. Pairing: the final paired-cue response was {paired:+.3f}, versus {control:+.3f} for cue-only exposure.")
print(f"2. Extinction: cue-only presentations changed the response from {start:+.3f} to {end:+.3f} ({metrics['extinction_retained_fraction']['mean']:.1%} retained).")
print(f"3. Reversal: bitter pairings changed mean cue value from {reversal_start:+.3f} to {reversal_end:+.3f}; {negative_share:.0%} of model initializations ended below zero.")
```

The model produces these patterns because its plasticity and decay rules were defined to do so: paired inputs strengthen a selected valence pathway, cue-only inputs decay learned weights, and the reversal protocol strengthens the opposing pathway. Reproducibility shows that the implementation follows its equations; it does **not** independently validate those equations as fly memory mechanisms.

The independent seeds alter which Kenyon cells respond to each odor, but this toy rule is symmetric across those cells, so replicate-level standard errors may be zero. This is not evidence of biological certainty. Better-supported biological claims would require matching the modeled pathway to FlyWire cell identities, validating dynamics and plasticity against fly experiments, and testing predictions not used to construct the model. The local FlyWire subgraph in the following chapter remains separate from these simulated results.
