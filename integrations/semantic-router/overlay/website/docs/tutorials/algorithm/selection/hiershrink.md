---
title: HierShrink
sidebar_position: 20
---

# HierShrink

## Overview

HierShrink is an experimental CPU selector for frozen mapped HierShrink profiles.
It selects the eligible model with the largest predicted quality minus weighted
artifact cost. It does not learn task importance or schedule tool execution.
The default routing policy does not change.

## What Problem Does It Solve?

It applies a frozen quality profile to candidate models with sparse observations.
The mapped profile combines a learned reference prediction with local residuals.
The serving path does not fit or update that profile.

## When to Use

Use it for controlled experiments with measured profiles and a matching encoder.
Keep fixed routing for models without profiles. Do not treat research benchmark
profiles as measurements of your incident backends.

## Export a profile

Use the compiled NPZ artifact from icr-router's MappedSelector. Install NumPy in
the offline export environment. Create a JSON mapping from every artifact model
ID to its real backend ID. Do not map one model's measurements to another model.

```sh
python tools/export_hiershrink.py profile.npz /models/hiershrink.json \
  --encoder bge --model-map backend-ids.json
```

The exporter refuses to overwrite an existing file. Use the exact frozen encoder,
weights, dimension, preprocessing and near-unit normalization used by the profile.
The encoder name is an operator declaration, not a weights checksum. Matching
dimensions alone does not establish compatibility. Configure the router embedding
provider to serve that encoder. The runtime checks the declared name and dimension.

## Configuration

```yaml
algorithm:
  type: hiershrink
  hiershrink:
    artifact_path: /models/hiershrink.json
    embedding_model: bge
    embedding_dimension: 768
    cost_weight: 0.1
```

Place this block in a decision with modelRefs that match the exported backend IDs.
Apply tool and context capability policies before selection. This selector only
uses the supplied candidates. It does not perform capability checks itself.
Equal utilities preserve candidate order. Costs retain the artifact's original
scale. They are not current provider prices. Confidence remains unset because
the quality estimate is not a calibrated confidence probability.

The router loads the artifact once per configuration on first use. It computes
an embedding with the configured encoder instead of reusing an unrelated signal
embedding. Subsequent selections use immutable in-process Go arrays. Restart the
router after replacing an artifact at the same path. Load and inference errors
use the router's existing default-candidate fallback. No strong-model fallback is
implicit. Put the intended fallback first in modelRefs and test error behavior.
The router bypasses selection when only one candidate remains.

Feedback requires an offline artifact rebuild. Adding a backend requires its own
measured profile. Removing a backend only restricts modelRefs. This implementation
does not claim better quality than UniRoute or the latency of the Python reference.
Measure Go selection, embedding, and end-to-end routing separately.
