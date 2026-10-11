"""Small, deterministic mushroom-body-inspired associative-memory model.

This is an explicit toy model for reproducible experiments, not a biological
simulation or a FlyWire-derived connectivity model.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class ModelParameters:
    kenyon_cells: int = 48
    active_cells: int = 8
    learning_rate: float = 0.16
    extinction_rate: float = 0.018
    seed: int = 4521


class MushroomBodyToy:
    """A sparse cue → KC → valence-output model with adjustable assumptions."""

    cues = ("A", "B")

    def __init__(self, parameters: ModelParameters | None = None):
        self.parameters = parameters or ModelParameters()
        p = self.parameters
        if p.kenyon_cells < 2 or not 1 <= p.active_cells <= p.kenyon_cells:
            raise ValueError("Require 1 <= active_cells <= kenyon_cells.")
        if not 0 < p.learning_rate <= 1 or not 0 <= p.extinction_rate <= 1:
            raise ValueError("Learning/extinction rates must be in their valid ranges.")

        rng = np.random.default_rng(p.seed)
        self.patterns = {
            cue: np.sort(rng.choice(p.kenyon_cells, p.active_cells, replace=False))
            for cue in self.cues
        }
        shape = (len(self.cues), p.kenyon_cells)
        self.appetitive = np.zeros(shape, dtype=np.float64)
        self.aversive = np.zeros(shape, dtype=np.float64)

    @staticmethod
    def _cue_index(cue: str) -> int:
        if cue not in ("A", "B"):
            raise ValueError("cue must be 'A' or 'B'.")
        return 0 if cue == "A" else 1

    @staticmethod
    def _valence(value: int | float) -> int:
        if value not in (-1, 1):
            raise ValueError("outcome must be +1 (appetitive) or -1 (aversive).")
        return int(value)

    def condition(self, cue: str, outcome: int) -> None:
        """Pair a cue and outcome; update a simple saturating eligibility rule."""
        index = self._cue_index(cue)
        outcome = self._valence(outcome)
        target, opponent = (
            (self.appetitive, self.aversive)
            if outcome > 0
            else (self.aversive, self.appetitive)
        )
        cells = self.patterns[cue]
        rate = self.parameters.learning_rate
        target[index, cells] += rate * (1 - target[index, cells])
        opponent[index, cells] *= 1 - rate * 0.18

    def extinction_trial(self, cue: str) -> None:
        """Present a cue without reinforcement; decay its two output weights."""
        index = self._cue_index(cue)
        cells = self.patterns[cue]
        factor = 1 - 3 * self.parameters.extinction_rate
        self.appetitive[index, cells] *= factor
        self.aversive[index, cells] *= factor

    def recall(self, cue: str) -> dict[str, float | str]:
        """Return the predicted valence during cue-only recall."""
        index = self._cue_index(cue)
        cells = self.patterns[cue]
        appetitive = float(self.appetitive[index, cells].mean())
        aversive = float(self.aversive[index, cells].mean())
        return {
            "cue": cue,
            "appetitive": appetitive,
            "aversive": aversive,
            "value": appetitive - aversive,
        }


def acquisition_experiment(
    *, replicates: int = 40, trials: int = 12, seed: int = 2026
) -> list[dict[str, int | str | float]]:
    """Compare paired conditioning with cue-only control exposures."""
    if replicates < 1 or trials < 1:
        raise ValueError("replicates and trials must both be positive.")
    records: list[dict[str, int | str | float]] = []
    for replicate in range(replicates):
        model = MushroomBodyToy(ModelParameters(seed=seed + replicate))
        for trial in range(1, trials + 1):
            model.condition("A", 1)
            records.append({"experiment": "acquisition", "group": "paired", "replicate": replicate, "trial": trial, **model.recall("A")})
            # Control cue exposures occur without a cue-contingent teaching signal.
            model.extinction_trial("B")
            records.append({"experiment": "acquisition", "group": "cue-only control", "replicate": replicate, "trial": trial, **model.recall("B")})
    return records


def extinction_experiment(
    *, replicates: int = 40, acquisition_trials: int = 10, extinction_trials: int = 16, seed: int = 3026
) -> list[dict[str, int | str | float]]:
    """Measure cue-only response loss after appetitive conditioning."""
    if replicates < 1 or acquisition_trials < 1 or extinction_trials < 1:
        raise ValueError("replicate and trial counts must be positive.")
    records: list[dict[str, int | str | float]] = []
    for replicate in range(replicates):
        model = MushroomBodyToy(ModelParameters(seed=seed + replicate))
        for _ in range(acquisition_trials):
            model.condition("A", 1)
        records.append({"experiment": "extinction", "phase": "after acquisition", "replicate": replicate, "trial": 0, **model.recall("A")})
        for trial in range(1, extinction_trials + 1):
            model.extinction_trial("A")
            records.append({"experiment": "extinction", "phase": "cue only", "replicate": replicate, "trial": trial, **model.recall("A")})
    return records


def reversal_experiment(
    *, replicates: int = 40, acquisition_trials: int = 10, reversal_trials: int = 16, seed: int = 4026
) -> list[dict[str, int | str | float]]:
    """Measure output-value change after switching sugar to bitter."""
    if replicates < 1 or acquisition_trials < 1 or reversal_trials < 1:
        raise ValueError("replicate and trial counts must be positive.")
    records: list[dict[str, int | str | float]] = []
    for replicate in range(replicates):
        model = MushroomBodyToy(ModelParameters(seed=seed + replicate))
        for trial in range(1, acquisition_trials + 1):
            model.condition("A", 1)
            records.append({"experiment": "reversal", "phase": "sugar", "replicate": replicate, "trial": trial, **model.recall("A")})
        for trial in range(1, reversal_trials + 1):
            model.condition("A", -1)
            records.append({"experiment": "reversal", "phase": "bitter reversal", "replicate": replicate, "trial": trial, **model.recall("A")})
    return records


def mean_sem(records: Iterable[dict], *, group_by: tuple[str, ...]) -> list[dict[str, int | str | float]]:
    """Aggregate values and standard errors without a pandas dependency."""
    groups: dict[tuple, list[float]] = defaultdict(list)
    for row in records:
        groups[tuple(row[key] for key in group_by)].append(float(row["value"]))
    result = []
    for key, values in sorted(groups.items(), key=lambda pair: pair[0]):
        array = np.asarray(values, dtype=np.float64)
        row = dict(zip(group_by, key))
        row["mean"] = float(array.mean())
        row["sem"] = float(array.std(ddof=1) / np.sqrt(len(array))) if len(array) > 1 else 0.0
        row["n"] = len(array)
        result.append(row)
    return result


def summarize_experiments(
    acquisition: list[dict], extinction: list[dict], reversal: list[dict]
) -> list[dict[str, str | float | int]]:
    """Process replicate-level records into pre-defined response metrics."""
    summaries: list[dict[str, str | float | int]] = []

    def add(metric: str, description: str, values: Iterable[float], unit: str = "approach − avoid") -> None:
        values_array = np.asarray(list(values), dtype=np.float64)
        if not len(values_array):
            raise ValueError(f"No observations available for {metric}.")
        sem = float(values_array.std(ddof=1) / np.sqrt(len(values_array))) if len(values_array) > 1 else 0.0
        if np.isclose(sem, 0.0, atol=1e-12):
            sem = 0.0
        summaries.append({"metric": metric, "description": description, "n": int(len(values_array)), "mean": float(values_array.mean()), "sem": sem, "unit": unit})

    paired_first = {int(row["replicate"]): float(row["value"]) for row in acquisition if row["group"] == "paired" and row["trial"] == 1}
    paired_last = {int(row["replicate"]): float(row["value"]) for row in acquisition if row["group"] == "paired" and row["trial"] == max(r["trial"] for r in acquisition if r["group"] == "paired")}
    control_last = {int(row["replicate"]): float(row["value"]) for row in acquisition if row["group"] == "cue-only control" and row["trial"] == max(r["trial"] for r in acquisition if r["group"] == "cue-only control")}
    paired_replicates = sorted(paired_last.keys() & control_last.keys())
    add("paired_after_first", "Paired cue after the first sugar pairing", (paired_first[key] for key in sorted(paired_first)))
    add("paired_at_acquisition_end", "Paired cue after the final sugar pairing", (paired_last[key] for key in paired_replicates))
    add("cue_only_control_at_acquisition_end", "Cue-only control after the same number of exposures", (control_last[key] for key in paired_replicates))
    add("paired_minus_control", "Paired minus cue-only control at acquisition end", (paired_last[key] - control_last[key] for key in paired_replicates))

    extinction_start = {int(row["replicate"]): float(row["value"]) for row in extinction if row["phase"] == "after acquisition"}
    extinction_end_trial = max(row["trial"] for row in extinction if row["phase"] == "cue only")
    extinction_end = {int(row["replicate"]): float(row["value"]) for row in extinction if row["phase"] == "cue only" and row["trial"] == extinction_end_trial}
    extinction_replicates = sorted(extinction_start.keys() & extinction_end.keys())
    add("extinction_start", "Cue value immediately after acquisition", (extinction_start[key] for key in extinction_replicates))
    add("extinction_end", f"Cue value after {extinction_end_trial} unreinforced presentations", (extinction_end[key] for key in extinction_replicates))
    add("extinction_retained_fraction", "Final cue value divided by post-acquisition value", (extinction_end[key] / extinction_start[key] for key in extinction_replicates if extinction_start[key] != 0), "fraction retained")

    reversal_start_trial = max(row["trial"] for row in reversal if row["phase"] == "sugar")
    reversal_end_trial = max(row["trial"] for row in reversal if row["phase"] == "bitter reversal")
    reversal_start = {int(row["replicate"]): float(row["value"]) for row in reversal if row["phase"] == "sugar" and row["trial"] == reversal_start_trial}
    reversal_end = {int(row["replicate"]): float(row["value"]) for row in reversal if row["phase"] == "bitter reversal" and row["trial"] == reversal_end_trial}
    reversal_replicates = sorted(reversal_start.keys() & reversal_end.keys())
    add("reversal_start", "Cue value immediately before reversal", (reversal_start[key] for key in reversal_replicates))
    add("reversal_end", f"Cue value after {reversal_end_trial} bitter pairings", (reversal_end[key] for key in reversal_replicates))
    add("reversal_negative_fraction", "Replicates with negative cue value after reversal", (float(reversal_end[key] < 0) for key in reversal_replicates), "fraction negative")
    return summaries
