# Memory Garden

A browser-only interactive sandbox for exploring associative learning in a **simplified, mushroom-body-inspired circuit**. It demonstrates paired-cue learning, recall, extinction, and reversal with no build step or server-side component.

The research book and reproducible experiments are in [`research/`](research/). The published book is available at [fly.castalia.institute/research](https://fly.castalia.institute/research/).

## Run it

Open `index.html` in a modern browser, or serve this folder with any static web server. The application uses local JavaScript and canvas; the optional typeface is fetched from Google Fonts. No experiment data is uploaded.

## What the prototype models

- Two odors each activate a deterministic sparse pattern among 48 modeled Kenyon cells.
- Appetitive and aversive mushroom-body output pathways have separate cue-associated weights.
- Pairing a cue with sugar or bitter applies a reward-modulated, saturating plasticity rule.
- Cue-only repetitions approximate extinction; reversing the outcome demonstrates reversal learning.
- Recall presents both cues without reinforcement and plots the resulting approach-versus-avoid value.

The model is an explanatory toy, **not a FlyWire-derived subnetwork**. Its neuron counts, cue projections, teaching rule, opponent pathways, and forgetting rule are illustrative assumptions. The adult connectome is a structural wiring map; it does not by itself provide synaptic plasticity parameters, an animal’s learned synaptic state, or a validated account of memory. The app does not claim biological or cognitive equivalence.

## Scientific starting points

- [FlyWire Connectome Data Explorer (Codex)](https://codex.flywire.ai/)
- Shiu et al., [A Drosophila computational brain model reveals sensorimotor processing](https://doi.org/10.1038/s41586-024-07763-9)
- [FlyWire whole-brain connectome data release](https://zenodo.org/records/10676866)

## Implementation

The simulation currently runs on the main JavaScript thread because the toy network is small. A larger connectome-derived model should move computation to a Web Worker and/or a WebAssembly module, with exported circuit data and parameter provenance kept separate from the browser interface.
