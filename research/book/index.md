---
title: Fly Memory Research
subtitle: Associative learning experiments and connectome exploration
---

This is the computational research companion to [Memory Garden](https://fly.castalia.institute/). It makes the toy memory experiment reproducible, records its assumptions, and provides a local workflow for inspecting real FlyWire FAFB connectivity.

## Two separate strands

1. **Memory model experiments** run locally or during the book build. They explore what a small, explicitly simplified associative circuit does under conditioning, extinction, and reversal.
2. **FlyWire exploration** operates on downloaded, versioned connectome exports. It helps select annotated mushroom-body neurons and inspect their one-hop connectivity, but it does not turn structural edges into an experimentally validated learning model.

Use the chapters to read the [methods](methods.md), run [experiments and plots](experiments.md), or [download and explore FlyWire data](flywire.md).

```{note}
The simulated circuit is synthetic and illustrative. Real FlyWire measurements are structural data, not records of the animal's learned synaptic weights or subjective cognition.
```
