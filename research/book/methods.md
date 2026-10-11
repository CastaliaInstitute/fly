---
title: Model and experimental methods
---

## Research question

How do paired cues, unreinforced cue exposure, and a changed outcome affect predicted cue value in a compact mushroom-body-inspired circuit?

## Model

Each cue activates a deterministic sparse subset of 48 toy Kenyon cells. Two abstract output populations represent appetitive and aversive value. A paired outcome changes the active cue-to-output weights by a saturating rule,

\[
w \leftarrow w + \eta(1-w),
\]

where \(\eta\) is an exposed learning-rate parameter. An opposing-valence weight receives a small multiplicative reduction. An unreinforced presentation decays the two weights by an exposed extinction factor. Cue-only recall reports mean appetitive weight minus mean aversive weight over the active cells.

These equations are intentionally simple and make no claim to reproduce dopamine timing, eligibility traces, compartment-specific plasticity, neuromodulatory state, or the detailed biology of Kenyon cells and mushroom-body output neurons. Changing them is encouraged; the parameter values are hypotheses for this sandbox, not measurements.

## Experiments

- **Acquisition:** repeated appetitive pairing compared with cue-only exposures in a control group.
- **Extinction:** acquire an appetitive response, then present the cue without reinforcement.
- **Reversal:** acquire an appetitive response, then pair the same cue with an aversive outcome.

Every model instance has an explicit random seed. Replicates vary the sparse cue patterns and are summarized by their mean and standard error. Simulation replicates are not biological animals and do not estimate biological uncertainty.

## Relation to FlyWire

FlyWire v783 contributes neuron IDs, annotations, and weighted anatomical edges to a separate exploration workflow. The first ingestion target is the annotated neighborhood of Kenyon cells, MBONs, and PAM/PPL1 dopamine neurons. The data are not used as simulated synaptic strengths in these experiments. Connecting measured edges to function, signs, or learning dynamics requires additional evidence and decisions that remain explicit future work.

## Reproducibility

See `research/requirements.txt` for the software environment, `research/src/fly_memory.py` for the model, and `research/tests/` for invariants. The book build re-executes its analysis cells. The local FlyWire pipeline records export hashes and its filtering parameters, keeps tokens out of notebooks, and stores data outside the public site.
